from pydantic import BaseModel


class Job(BaseModel):
    role: str
    description: str
    experience_level: str