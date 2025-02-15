from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Dict, List

class JobMatchOutput(BaseModel):
    job_roles: Dict[str, str] = Field(
        ..., description="Job roles with matching scores in percentage (only scores above 50%)"
    )
    missing_skills: List[str] = Field(
        ..., description="List of skills missing in the resume but required in the job description"
    )
    projects: str = Field(
        ..., description="Suggestions to include projects specifically related to the job"
    )
    work_experience: str = Field(
        ..., description="Improvements in the experience section of the resume according to the job"
    )
    professional_summary: str = Field(
        ..., description="Suggestions for improvement in the summary section to secure the job"
    )
    ATS: int = Field(
        ..., description="Calculated ATS score out of 100"
    )
    missing_keywords: List[str] = Field(
        ..., description="List of keywords that would improve the resume upon inclusion"
    )

OutputParser = JsonOutputParser(pydantic_object=JobMatchOutput)

prompt = PromptTemplate(
    template="""You are an AI specializing in resume evaluation and job matching. 
    Given a candidate's resume, job role, and job description, analyze and return a structured JSON response.

### **Context:**
- **Resume:** ```{resume_text}```
- **Job Role:** ```{job_role}```
- **Job Description:** ```{job_description}```

### **Output Format:**
{format_instructions}

### **Instructions:**
- Identify **all job roles** that match the resume with a matching score **above 50%**.
- List missing **skills** required for the job but not mentioned in the resume.
- Suggest **projects** that the candidate should include.
- Highlight **work experience improvements** needed to align with the job.
- Improve the **professional summary** to better match the role.
- Calculate the **ATS score** (out of 100).
- Suggest **missing keywords** that would improve the resume for job matching.

Ensure the response follows the exact JSON structure. Do not include additional text, only return the JSON response.""",
    input_variables=["resume_text", "job_role", "job_description"],
    partial_variables={"format_instructions": OutputParser.get_format_instructions()},
)