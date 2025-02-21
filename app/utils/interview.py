from gtts import gTTS
import os
import playsound as ps

import threading
import sounddevice as sd
import wave
import torch
import torchaudio
import numpy as np
import logging
import queue
import io
from typing import Union, BinaryIO

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.schemas.interview import OverallResult

logger = logging.getLogger(__name__)

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
        logger.error(f"Error in TTS: {e}")

def record_audio(filename, rate=16000, channels=1):
    """
    Records audio from the microphone and saves it to a file using sounddevice.
    The user can stop the recording manually by pressing Enter. The recorded
    audio is processed for noise removal before saving.

    Args:
        filename (str): The name of the file to save the recording.
        rate (int): Sampling rate for the recording.
        channels (int): Number of audio channels (1 for mono, 2 for stereo).
    """
    audio_queue = queue.Queue()
    stop_recording = threading.Event()

    def callback(indata, frames, time, status):
        """Callback function to store recorded audio in a queue."""
        if status:
            print(f"Recording error: {status}")
        audio_queue.put(indata.copy())  # Store the recorded chunk

    # Open a stream for real-time recording
    with sd.InputStream(samplerate=rate, channels=channels, dtype='int16', callback=callback):
        print("Recording... Press Enter to stop.")
        input()  # Wait for user input to stop recording
        stop_recording.set()  # Signal stop

    # Collect recorded audio
    audio_frames = []
    while not audio_queue.empty():
        audio_frames.append(audio_queue.get())

    # Convert to NumPy array
    if audio_frames:
        audio_data = np.concatenate(audio_frames, axis=0)

        # Save to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 2 bytes for 'int16' format
            wf.setframerate(rate)
            wf.writeframes(audio_data.astype(np.int16).tobytes())

    logger.info(f"Recording saved as {filename}")

async def audio_to_text_silero(audio_data: Union[bytes, BinaryIO]) -> str:
    """
    Converts audio data directly to text using the Silero speech-to-text model.
    
    Args:
        audio_data (Union[bytes, BinaryIO]): Raw audio data in WAV format received from WebSocket
        
    Returns:
        str: The transcribed text from the audio
    """
    try:
        # Create an in-memory buffer from the audio data
        if isinstance(audio_data, bytes):
            audio_buffer = io.BytesIO(audio_data)
        else:
            audio_buffer = audio_data

        # Load audio from buffer instead of file
        waveform, sample_rate = torchaudio.load(audio_buffer)
        logger.info(f"Waveform shape: {waveform.shape}, Sample rate: {sample_rate}")

        # Resample if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)

        # Convert to mono if stereo
        if waveform.ndim > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Normalize the waveform
        mean = waveform.mean()
        std = waveform.std() if waveform.std() > 0 else 1.0
        waveform = (waveform - mean) / std

        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)

        logger.info(f"Final Waveform shape: {waveform.shape}")

        # Load the Silero model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model, decoder, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_stt',
            language='en',
            device=device
        )
        logger.info("Silero STT model loaded")
        
        prepare_model_input = utils[-1]
        input_batch = prepare_model_input(waveform, device=device)

        # Transcribe the audio
        output = model(input_batch)
        transcription = decoder(output[0].cpu())
        logger.info(f"Transcription: {transcription}")
        
        return transcription

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""

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
