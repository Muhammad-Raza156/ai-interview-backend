from pydantic import BaseModel, Json
from uuid import UUID 


class JobInterviewForm(BaseModel):
    job_role: str
    industry: str
    company: str
    description: str
    interview_type: str
    experience_level: str


class ParsedResume(BaseModel):
    user_id: UUID
    parsed_sections: Json

    class Config:
        orm_mode = True
        from_attributes = True

class Job(BaseModel):
    user_id: UUID
    role: str
    industry: str
    company: str
    experience_level: str
    description: str
    interview_type: str

    class Config:
        orm_mode = True
        from_attributes = True

