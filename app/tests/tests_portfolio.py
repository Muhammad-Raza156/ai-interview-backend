import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app  # Assuming your FastAPI app is in main.py
from app.db.base import Base  # Assuming your base is defined here
from app.db.session import get_db_session
from app.models.db_models import User, UserPortfolio, PortfolioStatus
from app.core.config import settings
from app.api.v1.endpoints import portfolio_analysis
from unittest.mock import MagicMock
from app.utils.portfolio import validate_url
from app.schemas.portfolio import PortfolioCreate
from uuid import uuid4

# Use a test database
DATABASE_URL_TEST = settings.DATABASE_URL.replace("ai_interview", "test_ai_interview")

# Configure the engine for the test db
engine = create_async_engine(DATABASE_URL_TEST)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


# Dependency override for tests
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db

# Test client
client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
async def create_test_database():
    """
    Create a test database and tables for testing.
    """
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(autouse=True)
async def set_up_db():
    """
    Set up and tear down the test database before and after each test.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """
    Fixture to get a database session for a test.
    """
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def test_user(db_session):
    """
    Fixture to create a test user for testing.
    """
    user_id = uuid4()
    user = User(
        user_id=user_id,
        first_name="test",
        last_name="user",
        email="testuser@example.com",
        password="testpassword",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_upload_portfolio_success_new(db_session, test_user):
    """
    Test uploading a new portfolio URL successfully.
    """
    validate_url_mock = MagicMock(return_value=True)
    portfolio_analysis.validate_url = validate_url_mock
    portfolio_url = "https://www.example.com/my-portfolio"
    response = client.post(
        "/api/v1/portfolio/",
        data={"portfolio_url": portfolio_url},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Portfolio uploaded successfully"
    assert response.json()["portfolio"]["portfolio_url"] == portfolio_url
    assert response.json()["portfolio"]["status"] == "Pending"
    portfolio = await db_session.get(UserPortfolio, response.json()["portfolio"]["id"])
    assert portfolio
    assert portfolio.portfolio_url == portfolio_url
    assert portfolio.status == PortfolioStatus.PENDING


@pytest.mark.asyncio
async def test_upload_portfolio_success_update(db_session, test_user):
    """
    Test updating an existing portfolio URL successfully.
    """
    validate_url_mock = MagicMock(return_value=True)
    portfolio_analysis.validate_url = validate_url_mock
    # Create an existing portfolio
    existing_portfolio = UserPortfolio(
        user_id=test_user.user_id,
        portfolio_url="https://www.old-portfolio.com",
        status=PortfolioStatus.PENDING,
    )
    db_session.add(existing_portfolio)
    await db_session.commit()
    await db_session.refresh(existing_portfolio)
    
    new_portfolio_url = "https://www.new-portfolio.com"
    response = client.post(
        "/api/v1/portfolio/",
        data={"portfolio_url": new_portfolio_url},
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Portfolio URL updated successfully"
    assert response.json()["portfolio"]["portfolio_url"] == new_portfolio_url
    assert response.json()["portfolio"]["status"] == "Pending"
    updated_portfolio = await db_session.get(UserPortfolio, response.json()["portfolio"]["id"])
    assert updated_portfolio.portfolio_url == new_portfolio_url
    assert updated_portfolio.status == PortfolioStatus.PENDING


@pytest.mark.asyncio
async def test_upload_portfolio_invalid_url(db_session, test_user):
    """
    Test uploading a portfolio with an invalid URL.
    """
    validate_url_mock = MagicMock(return_value=False)
    portfolio_analysis.validate_url = validate_url_mock
    invalid_url = "invalid-url"
    response = client.post(
        "/api/v1/portfolio/",
        data={"portfolio_url": invalid_url},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or inaccessible portfolio URL"


@pytest.mark.asyncio
async def test_upload_portfolio_missing_url(db_session, test_user):
    """
    Test uploading a portfolio with a missing URL.
    """

    response = client.post(
        "/api/v1/portfolio/",
        data={},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 422

