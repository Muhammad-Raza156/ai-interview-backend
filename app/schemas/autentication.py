from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    first_name: str | None = None


class User(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str

