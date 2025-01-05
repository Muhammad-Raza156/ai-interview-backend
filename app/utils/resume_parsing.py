
from pdf2image import convert_from_bytes
import pytesseract
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from typing_extensions import Annotated, TypedDict
from langchain_cohere import ChatCohere
#import os
#os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\Tesseract-OCR\tessdata"
# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
cohere_api_key=settings.COHERE_API_KEY

# TypedDict
class ResumeResponse(TypedDict):
    """Relevant resume sections."""

    skills: Annotated[str, ..., "skills section of the given resume text"]
    experience: Annotated[str, ..., "work experience section of the given resume text"]
    years: Annotated[int, None, "total work experience in years "]
    education: Annotated[str, ..., "education section of the given resume text"]
    projects: Annotated[str, ..., "projects section of the resume"]

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
    #local_poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
    pdf_images=convert_from_bytes(pdf_content, dpi=300,  
                                  poppler_path='/usr/bin/')
    
    text=""
    for image in pdf_images:
        text += pytesseract.image_to_string(image)
    
    return text

async def resume_parsing_tempelate():
    resume_template = """
    Extract and organize the following sections from the given resume text:
    1. Education
    2. Skills
    3. Work Experience
    4. Years of Experience
    5. Projects

    Resume Text:
    {resume_text}
    Output the result as a JSON object with keys: education, skills, experience, projects, and years.
    """
    return PromptTemplate(template=resume_template, input_variables=["resume_text"])

async def llm_config(model_name="command-r-plus-08-2024", temperature=0.1):
    llm = ChatCohere(cohere_api_key=cohere_api_key, 
                     model=model_name, temperature=temperature)
    return llm