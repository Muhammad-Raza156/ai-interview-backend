from pydantic import BaseModel


class Job(BaseModel):
    role: str
    description: str
    difficulty_level: str