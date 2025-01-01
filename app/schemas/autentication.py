from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: UUID


class User(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str

