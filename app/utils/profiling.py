from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Dict, List

class JobMatchOutput(BaseModel):
    job_roles: Dict[str, str] = Field(
        ..., description="Job roles with matching scores in percentage (at least 10 suitable job roles for candidate)"
    )
    missing_skills: Dict[str, List[str]] = Field(
        ..., description="Categorized dictionary of missing skills based on skill type. The keys shall be skill categories such as 'technical_skills', 'soft_skills', 'Certifications', 'tools_technologies', and values shall be lists of missing skills."
    )
    projects: str = Field(
        ..., description="Suggestions to include projects specifically related to the job"
    )
    work_experience: Dict[str, any] = Field(
        ..., description="Work experience analysis including improvements, relevant job titles, industry experience, and qualification status."
    )
    professional_summary: Dict[str, any] = Field(
        ..., description="Analysis of the professional summary with relevance score and missing keywords."
    )
    ATS: int = Field(
        ..., description="Calculated ATS score out of 100"
    )
    missing_keywords: List[str] = Field(
        ..., description="List of keywords that would improve the resume upon inclusion"
    )
    model_config = {
        "arbitrary_types_allowed": True  # Allows Pydantic to handle complex types
    }
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
** Job Role Matching **
   - Identify at least **10 relevant job roles** the candidate is suitable for.
   - Assign a **matching score (in percentage)** for each job role based on the candidate’s skills and experience.
**Missing Skills:**
   - List **key skills the candidate lacks** that are essential for improving their job match.
   - Skills required for the job but not mentioned in the resume.
   - Skill will be missing if it is required in job description but not present in neither of Skills, Experience, or Projects sections of resume.
   - Categorize missing skills into the following types:
      - `"technical_skills"`: Missing **programming languages, frameworks, AI/ML, algorithms, etc.**
      - `"soft_skills"`: Missing **communication, teamwork, leadership, problem-solving skills, etc.**
      - `"tools_technologies"`: Missing **software tools, cloud platforms, DevOps tools, databases, etc.**
      - `"Certifications"`:List of **certifications** empty if no relevant certifications are found check certifications section in resume.

**Projects Analysis:**
    - Provide a **summary of important projects** from the resume that showcase relevant expertise.
    - Suggest **projects to include** that are specifically related to the job role.

**Work Experience Analysis:**
    - Highlight **work experience improvements** needed to align with the job.
    - Check whether **the candidate’s total industry experience** meets, exceeds, or falls short of the required experience in the job description.
    - Provide a **summary of relevant industry experience**, specifying the number of years and whether it is **near, equal to, or greater than** the required experience.
    - Identify **relevant job titles** from the candidate’s past roles that match the job role.
    - If no relevant job titles are found, return an empty list.
    - Include an **experience level evaluation**:
      - `"qualify"` → If the candidate's experience is **greater than or equal** to the required experience.
      - `"not qualify"` → If the candidate's experience is **less than** the required experience.
    - Example output structure:
      ```json
      "work_experience": {{
          "improvements": "AI-generated text providing recommendations",
          "relevant_titles": ["Software Engineer", "AI Engineer"],
          "industry_experience": "5 years",
          "experience_leve":"qualify"
      }}
      ```

**Professional Summary Analysis:**
    - Evaluate how well the **professional summary aligns** with the job description.
    - Provide a **relevance score (0-10)**.
    - Identify **missing keywords** that should be included to improve alignment.
    - If the summary is well-aligned with the job, return an empty list for missing keywords.
    - Example output structure:
      ```json
      "professional_summary": {{
          "relevance": AI-generated relevance score (integer between 0-10),
          "missing_keywords": ["Machine Learning", "Leadership", "Cloud Computing"]
      }}
      ```

**ATS Score:**
    - Calculate an **ATS compatibility score (0-100%)**, indicating how well the resume aligns with industry standards.

**Missing Keywords:**
    - Suggest **missing keywords** that would improve the resume for job matching.
    - List relevant **keywords missing from the resume** that could improve its visibility in ATS (Applicant Tracking Systems).

Ensure the response follows the exact JSON structure. Do not include additional text, only return the JSON response.""",
    input_variables=["resume_text", "job_role", "job_description"],
    partial_variables={"format_instructions": OutputParser.get_format_instructions()},
)