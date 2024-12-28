from fastapi import APIRouter, HTTPException
from fastapi import UploadFile, File
import cohere
from app.core.config import settings
import pytesseract
from pdf2image import convert_from_bytes



file_router = APIRouter()
co=cohere.ClientV2(settings.COHERE_API_KEY)

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

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
                                  poppler_path="/usr/bin")
    
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
async def upload_file(file: UploadFile=File(...)):
    
    """
    Uploads a resume in PDF format and extracts education from it using the Cohere AI model.

    Args:
        file (UploadFile): The PDF file containing the resume.

    Returns:
        dict: A dictionary with a single key "data" whose value is the extracted relevant resume information.

    Raises:
        HTTPException: If the file is not in PDF format.
    """

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()

    # Process the PDF content and get the text from it
    resume_text = await process_pdf(content)


    text=process_resume(resume_text)



    api_response = {
            "data": text
        }

    return api_response