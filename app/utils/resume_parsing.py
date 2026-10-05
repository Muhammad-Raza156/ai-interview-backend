from pdf2image import convert_from_bytes
import pytesseract
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from langchain_cohere import ChatCohere
from langchain_cohere import CohereEmbeddings
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from typing_extensions import Annotated, TypedDict
import platform


cohere_api_key = settings.COHERE_API_KEY

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
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Users\EliteBook\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        poppler_path=r"C:\Program Files\poppler-24.08.0\Library\bin"
    else:
        # Set Tesseract path
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        poppler_path = "/usr/bin/"
        
    pdf_images = convert_from_bytes(
        pdf_content, dpi=300, poppler_path=poppler_path
    )

    text = ""
    for image in pdf_images:
        text += pytesseract.image_to_string(image)

    return text


async def resume_parsing_template():
    resume_template = """
    Extract and organize the following sections from the given resume text:
    1. Education
    2. Skills
    3. Work Experience
    4. Years of Experience
    5. Projects
    6. Certifications

    Resume Text:
    {resume_text}
    Output the result as a JSON object with indentation of 4 spaces and keys: education, skills, experience, projects, years(experince in years), certifications (if any).
    """
    return PromptTemplate(template=resume_template, input_variables=["resume_text"])


async def key_sections_tempelate():
    key_sections_tempelate = """
    As an expert technical interviewer, analyze the job requirements and candidate's resume to identify 
    and describe key technical interview sections for a {job_role} position.
    
    Job Description:
    {job_description}
    
    Candidate's Resume Information:
    {resume_information}
    
    For each of these key interview sections:
    - technical_skills
    - system_design
    - problem_solving
    - domain_knowledge
    - project_experience
    
    Provide:
    1. A relevance score (1-10) based on job requirements and candidate profile
    2. 3-5 key points that must be covered during the interview
    3. List of specific required knowledge areas to assess
    4. Summary of candidate's relevant experience from their resume
    5. Suggested focus areas for the interviewer
    
    Format the response as a JSON object with the exact structure matching these keys with indentation of 4 spaces:
    {{
        "section_name": {{
            "relevance_score": integer,
            "key_points": [string],
            "required_knowledge": [string],
            "candidate_experience": string,
            "suggested_focus": string
        }}
    }}
    """
    return PromptTemplate(
        template=key_sections_tempelate,
        input_variables=["job_role", "job_description", "resume_information"],
    )

async def llm_config(model_name="command-r-plus-08-2024", temperature=0.1):
    llm = ChatCohere(
        cohere_api_key=cohere_api_key, model=model_name, temperature=temperature
    )
    return llm


embeddings = CohereEmbeddings(cohere_api_key=cohere_api_key, 
                             model="embed-multilingual-v3.0")

async def get_embedding(text: str) -> list[float]:
    """Generate embedding using Cohere AI embedding model."""
    try:
        # Generate embeddings using Langchain's CohereEmbeddings
        embedding = await embeddings.aembed_query(text)
        return embedding
    
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise

async def calculate_similarity_score(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors using sklearn and convert to a 0-10 score.
    
    Args:
        vec1 (List[float]): First vector
        vec2 (List[float]): Second vector
        
    Returns:
        float: Similarity score on a scale of 0-10, rounded to 2 decimal places
    """
    # Reshape vectors for sklearn's cosine_similarity function
    # cosine_similarity expects 2D arrays of shape (n_samples, n_features)
    v1 = np.array(vec1).reshape(1, -1)
    v2 = np.array(vec2).reshape(1, -1)
    
    # Calculate cosine similarity
    cos_sim = cosine_similarity(v1, v2)[0][0]  # Extract scalar value from 2D array
    
    # Convert similarity (-1 to 1) to a 0-10 score
    score = ((cos_sim + 1) / 2) * 10
    
    return round(score, 2)