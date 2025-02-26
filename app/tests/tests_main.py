from fastapi.testclient import TestClient
from app.db.session import get_db_session
from app.main import app
from unittest.mock import AsyncMock, patch
import pytest

client = TestClient(app)

@pytest.fixture
def override_get_db_session():
    async def _override_get_db_session():
        # Create an AsyncMock that represents your database session
        mock_db = AsyncMock()
        yield mock_db
    # Override the dependency in the app
    app.dependency_overrides[get_db_session] = _override_get_db_session
    yield  # tests run here
    # Clean up the override after the test
    app.dependency_overrides.pop(get_db_session, None)

@pytest.fixture
def access_token():
    login_data = {
        "email": "john.doe@example.com",
        "password": "securePassword123!"
    }
    response = client.post("/api/v1.0/login", json=login_data)
    assert response.status_code == 200
    return response.json().get("data", {}).get("access_token")
# def test_signup(): 
#         # Test the signup endpoint with a valid user
#     user_data = {
#             "first_name": "John",
#             "last_name": "Doe",
#             "email": "john.doe1@example.com",
#             "password": "securePassword123!"
#         }
#     response = client.post("/api/v1.0/Signup",json=user_data)
#     assert response.status_code == 200
#     assert response.json()== {"message":"User created successfully"}

# def test_signup_existing_email():
#     # Define the user data for signup
#     user_data = {
#         "first_name": "John",
#         "last_name": "Doe",
#         "email": "john.doe2@example.com",
#         "password": "securePassword123!"
#     }
    
#     # First signup attempt should succeed
#     response = client.post("/api/v1.0/Signup", json=user_data)
#     assert response.status_code == 200
#     #Expected response message may vary; adjust if needed:
#     assert response.json() == {"message": "User created successfully"}
    
#     # Second signup attempt with the same email should raise an error
#     response = client.post("/api/v1.0/Signup", json=user_data)
#     assert response.status_code == 409  
#     assert response.json() == {"detail":"User with this email already exists"}

def test_login():
    # Test the login endpoint with a valid user
    login_data={
        "email": "john.doe@example.com",
        "password": "securePassword123!"
    }
    response = client.post(
        "/api/v1.0/login",
        json=login_data,
    )
    assert response.status_code == 200
    assert "data" in response.json()
    return response.json().get("data").get("access_token")


def test_login_invalid_credentials():
    # Test login with invalid credentials
    login_data = {
        "email": "john.doe@example.com",
        "password": "wrongPassword"
    }
    response = client.post("/api/v1.0/login", json=login_data)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid email or password"
   }



# def test_submit_application():
#     # Get the access token
#     token = test_login()

#     # Prepare the request
#     file_path = r"C:\Users\AIMS TECH\Downloads\resume_data\resume.pdf"
#     with open(file_path, "rb") as file:
#         response = client.post(
#             "/api/v1.0/submit-application",
#             headers={"Authorization": f"Bearer {token}"},
#             files={"file": ("resume.pdf", file, "application/pdf")},
#             data={
#                 "job_role": "Software Engineer",
#                 "industry": "Tech",
#                 "company": "Example Corp",
#                 "description": "Job description",
#                 "interview_type": "Technical",
#                 "experience_level": "Mid-level"
#             }
#         )
    
#     # Assert the response
#     assert response.status_code == 200
#     assert "public_url" in response.json()


def test_submit_application_invalid_token():
    # Use an invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post(
        "/api/v1.0/submit-application",
        headers=headers,
        files={"file": ("resume.pdf", b"dummy content", "application/pdf")},
        data={
            "job_role": "Software Engineer",
            "industry": "Tech",
            "company": "Example Corp",
            "description": "Job description",
            "interview_type": "Technical",
            "experience_level": "Mid-level"
        }
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_submit_application_missing_token():
    # Make a request without a token
    response = client.post(
        "/api/v1.0/submit-application",
        files={"file": ("resume.pdf", b"dummy content", "application/pdf")},
        data={
            "job_role": "Software Engineer",
            "industry": "Tech",
            "company": "Example Corp",
            "description": "Job description",
            "interview_type": "Technical",
            "experience_level": "Mid-level"
        }
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}

def test_submit_application_invalid_file_type():
    # Get the access token
    token = test_login()

    # Submit a non-PDF file
    with open(r"C:\Users\AIMS TECH\Downloads\db_erd.png", "rb") as file:
        response = client.post(
            "/api/v1.0/submit-application",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test_image.png", file, "image/png")},
            data={
                "job_role": "Software Engineer",
                "industry": "Tech",
                "company": "Example Corp",
                "description": "Job description",
                "interview_type": "Technical",
                "experience_level": "Mid-level"
            }
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Only PDF files are allowed for the resume."}

# def test_file_parsing():
#     # Get the access token
#     token = test_login()

#     # Make a request to the file endpoint
#     response = client.post(
#         "/api/v1.0/file",
#         headers={"Authorization": f"Bearer {token}"}
#     )
    
#     # Assert the response
#     assert response.status_code == 200
#     assert "skills" in response.json()
#     assert "experience" in response.json()

# def test_file_parsing_invalid_token():
#     # Use an invalid token
#     headers = {"Authorization": "Bearer invalid_token"}
#     response = client.post("/api/v1.0/file", headers=headers)
#     assert response.status_code == 401
#     assert response.json() == {"detail": "Could not validate credentials"}

# def test_file_parsing_missing_token():
#     # Make a request without a token
#     response = client.post("/api/v1.0/file")
#     assert response.status_code == 401
#     assert response.json() == {"detail": "Not authenticated"}

# def test_file_parsing_no_resume():
#     # Get the access token
#     token = test_login()

#     # Make a request without uploading a resume
#     response = client.post(
#         "/api/v1.0/file",
#         headers={"Authorization": f"Bearer {token}"}
#     )
#     assert response.status_code == 404
#     assert response.json() == {"detail": "No resume found for the user"}