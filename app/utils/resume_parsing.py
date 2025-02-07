from pdf2image import convert_from_bytes
import pytesseract
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from langchain_cohere import ChatCohere
from langchain_cohere import CohereEmbeddings
from langchain_core.output_parsers import JsonOutputParser

from gtts import gTTS
import os
import playsound as ps

import speech_recognition as sr
import threading

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from typing_extensions import Annotated, TypedDict
import platform

from pydantic import Field, BaseModel, Json


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

    Resume Text:
    {resume_text}
    Output the result as a JSON object with indentation of 4 spaces and keys: education, skills, experience, projects, and years.
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
3. Answer to the question

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

For each section, generate 4 questions varying in difficulty.

Return the response as a JSON object matching this exact structure with indentation of 4 spaces:
{{
    "technical_knowledge": [
        {{
            "question": "string",
            "expected_answer_points": ["string"],
            "answer": ["string"],
        }}
    ],
    "system_design": [same structure],
    "problem_solving": [same structure],
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

async def evaluation_tempelate():
    evaluation_template = """
You are an expert technical interviewer and evaluator. Your task is to evaluate a candidate's response to an interview question 
with detailed feedback and scoring.

Context:

Question Asked: {question}

Model Answer (Key Points):
{model_answer}

Candidate's Response:
{candidate_answer}

Please evaluate the response considering:
1. Technical accuracy
2. Completeness of the answer
3. Clarity of explanation
4. Practical understanding
5. Proper use of technical terminology
6. Structured thinking
7. Real-world application awareness

Important Instructions:
- Score should be justified with specific examples from the response
- Provide actionable feedback for improvement
- Highlight both strengths and weaknesses
- Consider partial credit for partially correct explanations
- Account for different valid approaches to the solution
- Consider the expected experience level when evaluating
- Identify any bonus points for exceptional insights

{{format_instructions}}

Remember to:
1. Be objective and fair in scoring
2. Provide specific examples from the response
3. Give actionable improvement suggestions
4. Acknowledge alternative valid approaches
5. Consider both theoretical understanding and practical application
6. Evaluate communication clarity separately from technical accuracy

Think through your evaluation step by step:
1. First, identify the key points covered and missed
2. Then, assess the technical accuracy of each point
3. Consider the clarity and structure of the explanation
4. Evaluate practical understanding demonstrated
5. Compare against the model answer
6. Factor in the experience level expected
7. Calculate the final score
8. Formulate specific feedback points

Your evaluation should be constructive, actionable, and help the candidate improve, regardless of their performance level.

Return the response as a JSON object matching this exact structure with indentation of 4 spaces:
{{
    "score": float,
    "feedback": {{
        "type": string,
        "points": [string],
        "suggestions": [string],
        "missing_points": [string]
    }}
}}
"""

    return PromptTemplate(
        template=evaluation_template,
        input_variables=[
            "question",
            "model_answer",
            "candidate_answer",
        ],
    )


async def llm_config(model_name="command-r-plus-08-2024", temperature=0.1):
    llm = ChatCohere(
        cohere_api_key=cohere_api_key, model=model_name, temperature=temperature
    )
    return llm

def tts_speak(text: str, lang: str = "en"):
    """
    Converts text to speech and plays it.

    Args:
        text (str): The text to convert to speech.
        lang (str): The language of the text (default language is English).
    """
    try:
      # Generate speech from text
      tts = gTTS(text=text, lang=lang)
        
      #tts = gTTS(text)
      audio_file = "output.mp3"
      tts.save(audio_file)

      # Play the audio
      ps.playsound(audio_file)

        # Clean up the temporary file
      os.remove(audio_file)

    except Exception as e:
        print(f"Error in TTS: {e}")

    

def record_audio_with_stop():
    """
    Function to record audio until the 's' key is pressed.
    Uses Google Speech-to-Text API to transcribe the audio.
    """

    r = sr.Recognizer()
    global stop_recording
    stop_recording = False
    recognized_text = ""

    def listen_for_stop():
        """Background thread to listen for 's' key press to stop recording."""
        global stop_recording
        import keyboard  # Import here to avoid issues with threading
        print("Press 's' to stop recording.")
        while True:
            if keyboard.is_pressed("s"):
                stop_recording = True
                break

    # Start the background thread
    stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_thread.start()

    print("Listening...")

    while not stop_recording:
        try:
            # Use the microphone as source for input
            with sr.Microphone() as source2:
                # Wait for a second to let the recognizer
                # adjust the energy threshold based on
                # the surrounding noise level
                r.adjust_for_ambient_noise(source2, duration=0.2)
                
                # Listens for the user's input
                audio2 = r.listen(source2, timeout=5, phrase_time_limit=10)
                
                # Using Google to recognize audio
                MyText = r.recognize_google(audio2)
                MyText = MyText.lower()

                #print("Did you say:")
                print(MyText)
                recognized_text += MyText + " "

        except sr.WaitTimeoutError:
            print("Listening timeout - waiting for speech...")        
        except sr.RequestError as e:
            print(f"Could not request results: {e}")
            
        except sr.UnknownValueError:
            print("Unknown error occurred")

    print("Recording stopped.")
    return recognized_text.strip()

class SectionFeedback(BaseModel):
    score: int = Field(description="The user's score out of 10 for this section.")
    points_included: List[str] = Field(description="Points the user covered in their answers.")
    missing_points: List[str] = Field(description="Points the user missed in their answers.")
    suggestions: List[str] = Field(description="Suggestions to improve competency in this section.")

class OverallResult(BaseModel):
    technical_knowledge: SectionFeedback = Field(description="Feedback for the Technical Knowledge section.")
    system_design: SectionFeedback = Field(description="Feedback for the System Design section.")
    problem_solving: SectionFeedback = Field(description="Feedback for the Problem Solving section.")


output_parser = JsonOutputParser(pydantic_object=OverallResult)

async def result_tempelate():
    result_template = """
You are an AI interviewer analyzing the results of a user's interview. Below are the details:

Sections: Technical Knowledge, System Design, Problem Solving
Questions: {questions}
Results: {results}

Based on the above data, provide an overall result for the user. Include the following for each section:
1. Score (out of 10).
2. Feedback for each section, including:
   - Points included in the user's answers.
   - Missing points.
   - Suggestions to improve competency and learning in the section.

{format_instructions}
"""

    return PromptTemplate(
        template=result_template,
        input_variables=[
            "questions",
            "results",
        ],
        partial_variables={"format_instructions": output_parser.get_format_instructions()},
    )

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