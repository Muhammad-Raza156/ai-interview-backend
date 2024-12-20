from datetime import datetime, timedelta, timezone
from jwt import encode as jwt_encode
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext



from app.schemas.user import UserLogin, User, TokenData
from app.core.config import settings
from app.db.session import get_db_session
from app.models.user import User as UserModel


router = APIRouter()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

database_url = settings.database_url
# conn = psycopg2.connect(database_url)
#conn = psycopg2.connect(database_url)

def get_password_hash(password):
    """Hashes the given password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """Verifies whether the plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Creates a JWT token with an optional expiration time."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    token = jwt_encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


@router.post("/Signup")

async def signup(user: User, db: AsyncSession = Depends(get_db_session)):
    """Handles user signup by creating a new user in the database."""
    hashed_password = get_password_hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    new_user = UserModel(**user_data)
    db.add(new_user)
    
    try:
        await db.commit()
        await db.refresh(new_user)

        return {"message": "User registered successfully"}
    
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="email already exists")


@router.post("/login")
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db_session)):
    """Authenticates a user and returns an access token if valid."""
    stmt = select(UserModel).where(UserModel.email == user_login.email)
    stmt=select(UserModel).where(UserModel.email==user_login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    try:
        if not user or not verify_password(user_login.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))