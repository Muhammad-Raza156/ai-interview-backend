from fastapi import APIRouter, HTTPException, Depends, status
#from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import UploadFile, File, Form
import cohere
import pytesseract
from pdf2image import convert_from_bytes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
#from jose import JWTError
from supabase import create_client, Client

from app.core.config import settings
from app.schemas.autentication import TokenData
from app.db.session import get_db_session
from app.models.user import User as UserModel
from app.schemas.user_management import ViewUser





#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
bearer_scheme = HTTPBearer()

file_router = APIRouter()
co=cohere.ClientV2(settings.COHERE_API_KEY)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme) , db: AsyncSession = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},

    )
    token=credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
        token_data = TokenData(user_email=user_email)
         
        stmt=select(UserModel.user_id,UserModel.first_name,UserModel.last_name,UserModel.email).where(UserModel.email==token_data.user_email)
        result = await db.execute(stmt)
        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        db_user = result.first()
        if db_user is None:
            return {"error": "User not found"}
        user=ViewUser.from_orm(db_user)
        return user
    except jwt.DecodeError:
        raise credentials_exception

async def process_pdf(pdf_content):
    """
    Converts the content of a PDF file to text using OCR.

    Args:
        pdf_content (bytes): The byte content of the PDF file.

    Returns:
        str: The extracted text from the PDF.

    Converts PDF pages to images and then uses Tesseract OCR to extract
    text from these images. Requires the pdf2image and pytesseract 
    libraries, as well as a local installation of Tesseract OCR.
    """

    pdf_images=convert_from_bytes(pdf_content, dpi=300,  
                                  poppler_path='/usr/bin/')
    
    text=""
    for image in pdf_images:
        text += pytesseract.image_to_string(image)
    
    return text

def process_resume(resume_text):

    """
    Takes in a string of resume text and uses the Cohere command-r-plus-08-2024 model
    to extract education from the text.

    Args:
        resume_text (str): The text of the resume to be processed

    Returns:
        str: The extracted relevant resume information
    """

    response = co.chat(
    model="command-r-plus-08-2024", 
    messages=[{"role": "user", "content": f"""Extract skills, work experience, projects, and education\n
                from this text: {resume_text}\n
                response format: {"{"} "skills": [skill1, skill2, skill3], 
                "work experience": [work experience1, work experience2], 
                "projects": [project1, project2], 
                "education": [education1, education2] {"}"}\n
                 only the response in python dictionary  nothing else""" }]
)
    return response.message.content[0].text

@file_router.post("/file")
async def file_parsing(current_user: ViewUser = Depends(get_current_user)):
    
    """
    Retrieves and processes a user's resume file stored in Supabase storage.

    This function retrieves the first resume file associated with the current user
    from the Supabase storage. It then processes the PDF file to extract text, 
    and further processes the text to extract relevant resume information such as 
    skills, work experience, projects, and education using the Cohere model.

    Args:
        current_user (ViewUser): The current user authenticated and retrieved from 
        the token.

    Raises:
        HTTPException: If no files are found for the user, if the file cannot be 
        downloaded, or if any other error occurs during processing.

    Returns:
        dict: A dictionary containing the extracted relevant resume information.
    """
    try:
        user_id = current_user.user_id

        folder_path = f"resumes/users/{user_id}/"

        
        response=supabase.storage.from_("resumes").list(path=folder_path)
        if not response:
            raise HTTPException(status_code=404, detail="No files found for this user.")
            
        file_name = response[0]['name']
        #file_path=f"{folder_path}{file_name}"
        content= supabase.storage.from_("resumes").download(f"{folder_path}{file_name}")
        if  not content:
            raise HTTPException(status_code=404, detail="File not found.")

        resume_text = await process_pdf(content)
        text = process_resume(resume_text)
        return {"data": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



    

@file_router.post("/submit-application")
async def submit_application(job_role: str = Form(...), description: str = Form(...), 
                             difficulty_level: str = Form(...),
                             file: UploadFile=File(...),
                             current_user: ViewUser = Depends(get_current_user)):
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for the resume.")
    # save pdf to bucket on supabase

    user_id = current_user.user_id

    file_name = f"{user_id}_{file.filename}"
    folder_path = f"resumes/users/{user_id}/"

    try:
        file_content = await file.read()

        response = supabase.storage.from_("resumes").upload(f"{folder_path}{file_name}", file_content)

        if "data" not in response:
            raise HTTPException(status_code=500, detail="Failed to upload file to Supabase")
        
        file_url = supabase.storage.from_("resumes").get_public_url(f"{folder_path}{file_name}")

        return {"file":file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

