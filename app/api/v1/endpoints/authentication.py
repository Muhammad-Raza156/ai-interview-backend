from datetime import timedelta
#from jwt import encode as jwt_encode
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession



from app.schemas.autentication import UserLogin, User
from app.api.api_resonse import error_response, success_response
from app.db.session import get_db_session
from app.models.user import User as UserModel
from app.utils.authentication import verify_password, get_password_hash, create_access_token


auth_router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 60


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#database_url = settings.database_url


@auth_router.post("/Signup")

async def signup(user: User, db: AsyncSession = Depends(get_db_session)):
    """Handles user signup by creating a new user in the database."""
    stmt = select(UserModel).where(UserModel.email == user.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    hashed_password = get_password_hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    new_user = UserModel(**user_data)
    db.add(new_user)
    
    try:
        await db.commit()
        await db.refresh(new_user)
        return success_response(data="User created successfully")
    
    except IntegrityError as e:
        await db.rollback()
        return error_response(message=str(e))


@auth_router.post("/login")
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db_session)):
    """Authenticates a user and returns an access token if valid."""
    stmt=select(UserModel).where(UserModel.email==user_login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    try:
        if not user or not verify_password(user_login.password, user.password):
            raise error_response(message="Incorrect username or password")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
        data={"access_token": access_token, "token_type": "bearer"}
        return success_response(data=data)
    
    except Exception as e:
        raise error_response(message=str(e))
