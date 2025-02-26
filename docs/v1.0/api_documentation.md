# AI Interview Backend API Documentation

**API Version**: 0.1.0  
**Framework**: FastAPI  
**Date**: February 23, 2025  
**Base URL**: `/api/v1.0/` (versioned)

This document provides a comprehensive overview of the AI Interview Backend API, designed to support an AI-driven interview preparation platform. It includes endpoints for user management, resume analysis, interview preparation, and more. The API is built with FastAPI, leveraging automatic Swagger UI and ReDoc generation, and is intended for developers integrating with or extending the system.

---

## Table of Contents
1. [User Management](#user-management)
2. [Resume Analysis](#resume-analysis)
3. [Application](#application)
4. [Interview](#interview)
5. [Salary Negotiation](#salary-negotiation)
6. [Learning Paths](#learning-paths)

---

## User Management

### `POST /api/v1.0/Signup`
- **Description**: Registers a new user by storing their details in the database with a hashed password. Ensures email uniqueness.
- **Tags**: Authentication
- **Authentication**: None (public endpoint)
- **Request**:
  - **Method**: POST
  - **Content-Type**: `application/json`
  - **Body**:
    ```json
    {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "password": "SecurePass123!"
    }
- **Response**:
- **200 OK**:
  ```json
    {
    "message": "User registered successfully"
    }
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```
- **Raises**: 
- **HTTPException 400**: If email already exists.
- **Example Usage**:
```bash
curl -X POST "http://localhost:8000/api/v1.0/Signup" \
     -H "Content-Type: application/json"\
     -d '{"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "password": "SecurePass123!"}'
```

### `POST /api/v1.0/login`
- **Description**: Authenticates a user and returns a JWT token for subsequent requests.
- **Tags**: Authentication
- **Authentication**: None (public endpoint)
- **Request**:
  - **Method**: POST
  - **Content-Type**: `application/json`
  - **Body**:
  ```json
    {
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
    }
  ```
- **Response**:
- **200 OK**:
  ```json
  {
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
  }
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
- **Raises**: 
- **HTTPException 401**: If credentials are invalid.
- **Example Usage**:
```bash
curl -X POST "http://localhost:8000/api/v1.0/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "john.doe@example.com", "password": "SecurePass123!"}'
```

### `GET /api/v1.0/users/{user_mail}`
- **Description**: Retrieves user details by email.
- **Tags**: User Management
- **Authentication**: None (public, though typically authenticated in practice)
- **Request**:
  - **Method**: GET
  - **Path Parameter**: `user_mail`(e.g., `john.doe@example.com`)
- **Response**:
- **200 OK**:
  ```json
  [
    {
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com"
    }
  ]
  ```  
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["path", "user_mail"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```
- **Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/v1.0/users/john.doe@example.com"
```

### `GET /api/v1.0/view-users`
- **Description**: Retrieves a paginated list of all users.
- **Tags**: User Management
- **Authentication**: None (public endpoint)
- **Request**:
  - **Method**: GET
  - **Query Parameters**:
  - `page` (optional, default `1`)
  - `size` (optional, default `25`, max `25`)
  - **Example**: `/api/v1.0/view-users?page=1&size=25`
- **Response**:
- **200 OK**:
  ```json
    {
    "users": [
      {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com"
      }
    ],
    "total_users": 1,
    "total_pages": 1,
    "current_page": 1,
    "has_next": false,
    "has_previous": false
  }
  ```
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["query", "size"],
      "msg": "ensure this value is less than or equal to 25",
      "type": "value_error.number.not_le"
    }
  ]
}
```
- **Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/v1.0/view-users?page=1&size=25"
```

### `PATCH /api/v1.0/update-email`
- **Description**: Updates a user’s email address.
- **Tags**: User Management
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: PATCH
  - **Query Parameters**:
  - `old_email` (required)
  - `new_email` (required)
  - **Headers**: `Authorization: Bearer <token>`
  - **Example**: `/api/v1.0/update-email?old_email=john.doe@example.com&new_email=john.new@example.com`
- **Response**:
- **200 OK**:
  ```json
  {
  "message": "Email updated successfully"
  }
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["query", "new_email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```
- **Raises**: 
- **HTTPException 404**: If old email not found.
- **Example Usage**:
```bash
curl -X PATCH "http://localhost:8000/api/v1.0/update-email?old_email=john.doe@example.com&new_email=john.new@example.com" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### `PATCH /api/v1.0/update-password`
- **Description**: Updates a user’s password after verifying the old one.
- **Tags**: User Management
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: PATCH
  - **Query Parameters**:
  - `email` (required)
  - `old_password` (required)
  - `new_password` (required)
  - **Headers**: `Authorization: Bearer <token>`
  - **Example**: `/api/v1.0/update-password?email=john.doe@example.com&old_password=SecurePass123!&new_password=NewPass456!`
- **Response**:
- **200 OK**:
  ```json
  {
  "message": "Password updated successfully"
  }
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["query", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
- **Raises**: 
- **HTTPException 401**: If old password is incorrect.
- **Example Usage**:
```bash
curl -X PATCH "http://localhost:8000/api/v1.0/update-password?email=john.doe@example.com&old_password=SecurePass123!&new_password=NewPass456!" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Resume Analysis
### `GET /api/v1.0/resume_analysis`

- **Description**: Retrieves and analyzes a user’s profiling data (resume, job details) from Redis or database, prompt with the Cohere api, generates detailed profile analysis of user.
- **Tags**: Resume Analysis
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: GET
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
    {
    "profiling_result": {
      "job_roles": {
        "ML Engineer": "88%",
        "AI Engineer": "82%",
        "Data Scientist": "78%",
        "Software Engineer": "74%",
        "Python Developer": "69%",
        "Research Scientist": "64%",
        "Computer Vision Engineer": "60%",
        "NLP Engineer": "56%",
        "Deep Learning Engineer": "52%",
        "Data Engineer": "48%"
      },
      "missing_skills": {
        "technical_skills": [
          "Hyperparameter Tuning",
          "Feature Engineering",
          "Model Optimization",
          "Statistical Analysis"
        ],
        "soft_skills": [
          "Leadership",
          "Public Speaking"
        ],
        "tools_technologies": [
          "Docker",
          "Kubernetes",
          "CI/CD Pipelines"
        ],
        "Certifications": [
          "AWS Certified Machine Learning Specialty"
        ]
      },
      "projects": "Include projects that demonstrate experience in deep learning, NLP, and cloud-based deployments. Highlight work with data preprocessing, model optimization, and API development. Showcase contributions to open-source projects and research initiatives.",
      "work_experience": {
        "improvements": "Expand details about your role in previous projects, specifying contributions to model development, deployment, and data pipeline management. Highlight collaborations and problem-solving examples.",
        "relevant_titles": [
          "Machine Learning Engineer",
          "Software Developer"
        ],
        "industry_experience": "2 years",
        "experience_level": "qualify",
        "non_industrial_experience": {
          "Research": "1.5 years",
          "Teaching": "1 year"
        }
      },
      "professional_summary": {
        "relevance": 8,
        "missing_keywords": [
          "End-to-End ML Pipelines",
          "Data Engineering",
          "Cloud Computing",
          "API Development",
          "Collaboration",
          "Communication"
        ]
      },
      "ATS": 85,
      "missing_keywords": [
        "Machine Learning",
        "Cloud Platforms",
        "Data Engineering",
        "Feature Engineering",
        "Model Deployment",
        "Optimization Techniques",
        "Version Control"
      ]
    }
  }
  ```
- **Raises**: 
- **HTTPException 404**: If data not found.
- **Example Usage**:
```bash
curl -X GET "http://localhost:8000/api/v1.0/resume_analysis" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### `GET /api/v1.0/similarity`
- **Description**: Calculates the similarity score between a user’s resume and job description.
- **Tags**: Text Similarity
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: GET
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
  {
  "similarity_score": 0.87,
  "job_role": "Software Engineer",
  "resume_sections": ["skills", "experience"]
  }
  ```
- **Raises**: 
- **HTTPException 404**: If data not found.
- **Example Usage**:
```bash
curl -X GET "http://localhost:8000/api/v1.0/similarity" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
## Application
### `POST /api/v1.0/submit-application`
- **Description**:Submits a job application with a PDF resume, processes it with OCR and Cohere, and uploads to Supabase.
- **Tags**:Application
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: POST
  - **Content-Type**: `multipart/form-data`
  - **Headers**: `Authorization: Bearer <token>`
  - **Body**:
  ```bash
    job_role=Software Engineer
    industry=Tech
    company=TechCorp
    description=Develop scalable APIs
    interview_type=Technical
    experience_level=Mid
    file=@resume.pdf
  ```
- **Response**:
- **200 OK**:
  ```json
    {
    "url": "https://supabase.co/storage/resume.pdf"
  }
  ```
- **422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "file"],
      "msg": "File must be PDF",
      "type": "value_error"
    }
  ]
}
```
- **Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1.0/submit-application" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     -F "job_role=Software Engineer" \
     -F "industry=Tech" \
     -F "company=TechCorp" \
     -F "description=Develop scalable APIs" \
     -F "interview_type=Technical" \
     -F "experience_level=Mid" \
     -F "file=@resume.pdf"
```

### `POST /api/v1.0/file`
- **Description**:Parses a user’s resume from Supabase storage using Cohere.
- **Tags**:Application
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: POST
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
    {
      "education":{
        "degree":"",
        "university":"",
        "year":""
      },
      "skills": [
          "Python",
          "Machine Learning",
          "Deep Learning",
          "Natural Language Processing",
          "FastAPI",
          "PostgreSQL",
          "Cloud Computing (AWS, GCP)",
          "DevOps (Docker, Kubernetes)",
          "Data Preprocessing",
          "Model Deployment"
      ],
      "experience": [
      ],
      "years":"3 years",
      "projects": [
      ],
      "certifications": [
          "AWS Certified Machine Learning - Specialty",
          "TensorFlow Developer Certificate"
      ]
  }

  ```
- **Raises**: 
- **HTTPException 404**: If file not found.
- **Example Usage**:
```bash
curl -X POST "http://localhost:8000/api/v1.0/file" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
### `POST /api/v1.0/key-sections`
- **Description**:Generates key interview sections from resume and job details.
- **Tags**:Application
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: POST
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
  {
    "job_role": "Software Engineer",
    "sections": {
      "technical_skills": ["Python", "SQL"],
      "system_design": "Scalable API design"
    }
  }

  ```
- **Raises**: 
- **HTTPException 404**: If data not found.
- **Example Usage**:
```bash
curl -X POST "http://localhost:8000/api/v1.0/key-sections" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Interview
### `POST /api/v1.0/generate-interview-questions`
- **Description**: Generates tailored interview questions based on job details and resume, cached in Redis.
- **Tags**: Interview
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: POST
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
  {
    "job_role": "Software Engineer",
    "interview_questions": {
      "section1": [{
        "question": "What is your experience with Python?",
        "model_answer": "text",
        "expected_answer_points":[
          "1. ", "2. "
        ]
      }]
    }
  }
  ```
- **Raises**: 
- **HTTPException 404**: If data not found.
- **Example Usage**:
```bash
curl -X POST "http://localhost:8000/api/v1.0/generate-interview-questions" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### `GET /api/v1.0/result`
- **Description**: Retrieves the overall interview result for the current user.\n\n
This function fetches the cached interview evaluation result data for the current user\n
from the Redis cache. It then processes this data to compute the overall interview \n
result using a language model and a result template.\n\n
Args:\n    
current_user (ViewUser): The current authenticated user.
\n\nReturns:\n    
dict: A dictionary containing the user ID and the overall interview result.
- **Tags**: Interview
- **Authentication**: Requires `HTTPBearer` token
- **Request**:
  - **Method**: GET
  - **Headers**: `Authorization: Bearer <token>`
- **Response**:
- **200 OK**:
  ```json
    {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "result": {
    }
  }
  ```
- **Raises**: 
- **HTTPException 404**: If data not found.
- **Example Usage**:
```bash
curl -X GET "http://localhost:8000/api/v1.0/result" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```