## Endpoints
### 1.Authentication

**URL:** [text](http://127.0.0.1:8000/api/v1.0/Signup)
**Method:** POST

Registers a new user in the database.

This endpoint allows for user registration by accepting a user schema and storing it in the database after hashing the password. If the email is already in use, it raises an HTTP 400 error.

**Request Body**
json
'''
 {
  "first_name": "string",
  "last_name": "string",
  "email": "user@example.com",
  "password": "string"
}
'''

Args: user (User): The user data to register. db (AsyncSession, optional): The database session dependency.

Returns: dict: A success message indicating successful registration.

**Response**
*200:Successful*
'''
{"message": "User registered successfully"}    
'''

Raises: HTTPException: If there is a database integrity error, such as a duplicate email.

*400: Error*
Bad Request
'''
{
    "detail": "error detail"
}
'''

**URL:** [text](http://127.0.0.1:8000/api/v1.0/login)
**Method:** POST

Authenticates a user and returns a JWT token.

This endpoint allows for user authentication using their email and password. If the credentials are valid, it returns a JWT token that can be used to access protected endpoints.

Args: user_login (UserLogin): The user credentials to authenticate. db (AsyncSession, optional): The database session dependency.

**Request Body**
'''
{
  "email": "user@example.com",
  "password": "string"
}
'''
*Note:* minimum length of password shall be 8 while max 10

**Response**
Returns: dict: A dictionary containing the JWT token and the token type.
*200:Successful*
'''
 {
            "data": {
                "access_token": "string",
                "token_type": "type"
            }
        }

'''

*500:Error*
Raises: HTTPException: If the credentials are invalid, or if there is an internal error.
'''
{
  "detail": "401: Invalid credentials"
}
'''


### 2.Upload Resume

**URL:** [text](http://127.0.0.1:8000/api/v1.0/upload_resume)
**Method:** POST

Uploads a resume in PDF format and extracts education from it using the Cohere AI model.

**Request Body**
Args: file (UploadFile): The PDF file containing the resume.

**Response**
*200:Successful*
Returns: dict: A dictionary with a single key "data" whose value is the extracted relevant resume information from user uploaded file.

'''
{
    "data":"{
        "skills":list of skills,
        "work experience":list of experiences,
        "projects": list of projects,
        "education":list of educations
    }"
}

*400:Error*
Raises: HTTPException: If the file is not in PDF format.
'''
{
  "detail": "Only PDF files are allowed."
}
'''