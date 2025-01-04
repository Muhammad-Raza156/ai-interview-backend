from pydantic import BaseModel
from typing import List
from uuid import UUID 

class ViewUser(BaseModel):
    user_id: UUID
    first_name: str
    last_name: str
    email: str

    class Config:
        orm_mode = True
        from_attributes = True


class PaginatedUserResponse(BaseModel):
    users: List[ViewUser]
    total_users: int
    total_pages: int
    current_page: int
    has_next: bool
    has_previous: bool