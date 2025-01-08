from pydantic import BaseModel, EmailStr



class User(BaseModel):
    first_name: str 
    last_name: str 
    email: EmailStr 
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenData(BaseModel):
    user_email: str