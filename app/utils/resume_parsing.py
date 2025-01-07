from pdf2image import convert_from_bytes
import pytesseract
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from langchain_cohere import ChatCohere

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
cohere_api_key = settings.COHERE_API_KEY


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
    # local_poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"
    dokcer_poppler_path = "/usr/bin/"
    pdf_images = convert_from_bytes(
        pdf_content, dpi=300, poppler_path=dokcer_poppler_path
    )

    text = ""
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
    
    Format the response as a JSON object with the exact structure matching these keys:
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


async def questions_tempelate():
    question_template =  """You are an expert technical interviewer for a {job_role} position. Generate a comprehensive set of interview questions based on the following information:

JOB DESCRIPTION:
{job_description}

CANDIDATE'S RESUME:
{resume_data}

INTERVIEW SECTIONS AND THEIR RELEVANCE:
{interview_sections}

Task: Generate specific interview questions for each section. For each question, include:
1. The actual question
2. Expected key points in the answer
3. Difficulty level (Easy/Medium/Hard)
4. Evaluation criteria
5. Follow-up questions

Guidelines for Different Question Types:

TECHNICAL KNOWLEDGE QUESTIONS:
- Focus on specific technologies mentioned in both resume and job description
- Include questions about best practices and real-world applications
- Cover both fundamental concepts and advanced topics

SYSTEM DESIGN QUESTIONS:
- Focus on scalability, performance, and architectural decisions
- Include trade-off discussions
- Relate to the scale mentioned in the job description

PROBLEM-SOLVING QUESTIONS:
- Include both algorithmic and logical reasoning questions
- Focus on problem-solving approach rather than just the solution
- Cover edge cases and optimization

CODING CHALLENGE QUESTIONS:
- Must include clear input/output examples
- Should test both implementation and optimization skills
- Cover important concepts like error handling and edge cases

PROJECT DISCUSSION QUESTIONS:
- Based on candidate's past projects from resume
- Focus on technical decisions and trade-offs
- Include questions about challenges and solutions

For each section, generate 3 questions varying in difficulty.

Return the response as a JSON object matching this exact structure:
{{
    "technical_knowledge": [
        {{
            "question": "string",
            "expected_answer_points": ["string"],
            "difficulty_level": "string",
            "evaluation_criteria": ["string"],
            "follow_up_questions": ["string"]
        }}
    ],
    "system_design": [same structure],
    "problem_solving": [same structure],
    "coding_challenge": [same structure],
    "project_discussion": [same structure]
}}"""

    return PromptTemplate(
        template=question_template,
        input_variables=[
            "job_role",
            "job_description",
            "resume_data",
            "key_sections",
        ],
    )


async def llm_config(model_name="command-r-plus-08-2024", temperature=0.1):
    llm = ChatCohere(
        cohere_api_key=cohere_api_key, model=model_name, temperature=temperature
    )
    return llm
