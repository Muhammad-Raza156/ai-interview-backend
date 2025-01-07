from datetime import timedelta
import logging
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession


from app.schemas.autentication import UserLogin, User
from app.api.api_resonse import error_response, success_response
from app.db.session import get_db_session
from app.models.db_models import User as UserModel
from app.utils.authentication import (
    verify_password,
    get_password_hash,
    create_access_token,
)

logger = logging.getLogger(__name__)



auth_router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 60


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@auth_router.post("/Signup")
async def signup(user: User, db: AsyncSession = Depends(get_db_session)):
    """
    Registers a new user in the database.

    This function handles user registration by accepting a user object, checking
    if the email already exists in the database, and then creating a new user
    with a hashed password if no existing user is found.

    Args:
        user (User): The user data to register.
        db (AsyncSession, optional): The database session dependency.

    Raises:
        HTTPException: If a user with the given email already exists.
        IntegrityError: If there is a database integrity error.

    Returns:
        dict: A success message indicating successful registration.
    """

    stmt = select(UserModel).where(UserModel.email == user.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.error("User with this email already exists")
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    hashed_password = get_password_hash(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    new_user = UserModel(**user_data)
    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)
        logger.info("User created successfully")
        return success_response(data="User created successfully")

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return error_response(message=str(e))


@auth_router.post("/login")
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db_session)):
    """
    Authenticates a user and returns a JWT token.

    Args:
        user_login (UserLogin): The user credentials to authenticate.
        db (AsyncSession, optional): The database session dependency.

    Raises:
        HTTPException: If the user with the given email does not exist or the password is incorrect.
        Exception: If there is an error with the database.

    Returns:
        dict: A JSON response with the access token and its type.
    """
    stmt = select(UserModel).where(UserModel.email == user_login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    try:
        if not user or not verify_password(user_login.password, user.password):
            logger.error("Incorrect username or password")
            raise error_response(message="Incorrect username or password")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        data = {"access_token": access_token, "token_type": "bearer"}
        logger.info(
            f"User logged in successfully token expirse in {ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
        )
        return success_response(data=data)

    except Exception as e:
        logger.error(f"Error logging in user: {str(e)}")
        raise error_response(message=str(e))
