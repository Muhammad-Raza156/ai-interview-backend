from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.models.db_models import UserPortfolio, PortfolioStatus
from app.schemas.user_management import ViewUser
from app.utils.user_management import get_current_user
from app.schemas.portfolio import(
     PortfolioCreate, PortfolioURL, PortfolioUpdate, Portfolio
)
from app.utils.portfolio import validate_url
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

portfolio_router = APIRouter()


@portfolio_router.post("/portfolio/upload-portfolio")
async def upload_portfolio(
    portfolio_url: PortfolioURL,
    db: AsyncSession = Depends(get_db_session),
    current_user: ViewUser = Depends(get_current_user)
):
    """
    Upload or update a user's portfolio information, including LinkedIn and GitHub URLs.

    This endpoint allows a user to provide or update their LinkedIn and/or GitHub profile URLs.
    It also validates the accessibility of the provided URLs.

    - **linkedin_url**: (Optional) The URL of the user's LinkedIn profile.
    - **github_url**: (required) The URL of the user's GitHub profile.
    """
    if portfolio_url.linkedin_url:
        if not validate_url(portfolio_url.linkedin_url):
            logger.error(f"Invalid LinkedIn URL: {portfolio_url.linkedin_url}")
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")
    if portfolio_url.github_url:
        if not validate_url(portfolio_url.github_url):
            logger.error(f"Invalid GitHub URL: {portfolio_url.github_url}")
            raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    query = select(UserPortfolio).where(
        UserPortfolio.user_id == current_user.user_id
    )
    existing_portfolio = await db.execute(query)
    existing_portfolio = existing_portfolio.scalar_one_or_none()
    
    if existing_portfolio:
        if portfolio_url.linkedin_url:
            existing_portfolio.linkedin_url = portfolio_url.linkedin_url
        if portfolio_url.github_url:
            existing_portfolio.github_url = portfolio_url.github_url
        existing_portfolio.status = PortfolioStatus.PENDING
        await db.commit()
        logger.info(f"Portfolio URL updated successfully for user: {current_user.user_id}")
        await db.refresh(existing_portfolio)
        return {"message": "Portfolio URL updated successfully", "portfolio": existing_portfolio}

    portfolio_data = PortfolioCreate(
        user_id=current_user.user_id, 
        linkedin_url=portfolio_url.linkedin_url, 
        github_url=portfolio_url.github_url
    )
    db_portfolio = UserPortfolio(**portfolio_data.dict())
    db.add(db_portfolio)
    await db.commit()
    logger.info(f"Portfolio uploaded successfully for user: {current_user.user_id}")
    await db.refresh(db_portfolio)
    return {"message": "Portfolio uploaded successfully", "portfolio": db_portfolio}

# @portfolio_router.post("/portfolio/analysis")
# async def portfolio_analysis(db: AsyncSession = Depends(get_db_session),
#                              current_user: ViewUser = Depends(get_current_user)):
