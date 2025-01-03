from pydantic import BaseModel, EmailStr



class User(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenData(BaseModel):
    user_email: str