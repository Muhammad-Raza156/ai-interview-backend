from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from fastapi_pagination import add_pagination
from typing import Any
from math import ceil



from app.api.api_resonse import error_response
from app.db.session import get_db_session
from app.models.db_models import User as UserModel
from app.schemas.user_management import PaginatedUserResponse, ViewUser
from app.api.v1.endpoints.authentication import verify_password, get_password_hash
from app.utils.user_management import get_current_user

user_router = APIRouter()
add_pagination(user_router)

@user_router.get("/users/{user_mail}")
async def read_users(user_mail: EmailStr, db: AsyncSession = Depends(get_db_session)):
    """Returns a list of all user objects in the database."""
    try:
        stmt = select(UserModel.user_id, UserModel.first_name, UserModel.last_name, UserModel.email).where(UserModel.email == user_mail)
        result = await db.execute(stmt)
        users  = [ViewUser.from_orm(user) for user in result]
        return users
    
    except Exception as e:
        return error_response(message=str(e))
    


@user_router.get("/view-users", response_model=PaginatedUserResponse)
async def view_users(
    page: int = Query(1, gt=0, description="Page number"),
    size: int = Query(25, gt=0, le=25, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns a list of all user objects in the database."""
    try:
        total_users_query = select(func.count(UserModel.user_id))
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar()
        total_pages = ceil(total_users/size)
        if page > total_pages:
            raise HTTPException(status_code=404, detail="Page not found")
        users_query = select(
               UserModel.user_id, UserModel.first_name, UserModel.last_name, UserModel.email
               )
        users = await db.execute(users_query.limit(size).offset((page-1)*size))
        return PaginatedUserResponse(users= [ViewUser.from_orm(user) for user in users], total_users=total_users, total_pages=total_pages, current_page=page, has_next=page < total_pages, has_previous=page > 1)
    
    except Exception as e:
        return error_response(message=str(e))
    

@user_router.patch("/update-email")
async def update_user_email(
    old_email: EmailStr, new_email: EmailStr, 
    db: AsyncSession = Depends(get_db_session), current_user: ViewUser = Depends(get_current_user)
):
    """
    Updates the email of a user in the database.

    Args:
        old_email (EmailStr): The old email of the user.
        new_email (EmailStr): The new email of the user.

    Raises:
        HTTPException: If the user with the old email is not found.
        Exception: If there is an error with the database.

    Returns:
        dict: A JSON response with a success message.
    """
    user_id=current_user.user_id
    try:
        if old_email != current_user.email:
            raise HTTPException(status_code=400, detail="Unauthorized")
        stmt = select(UserModel).where(UserModel.email == old_email, UserModel.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User with this email not found")
        user.email = new_email
        await db.commit()
        return {"message": "User email updated successfully"}
    except Exception as e:
        await db.rollback()
        return error_response(message=str(e))


@user_router.patch("/update-password")
async def update_user_password(
    email: EmailStr, old_password: str, new_password: str, 
    db: AsyncSession = Depends(get_db_session), current_user: ViewUser = Depends(get_current_user)
):
    """
    Updates the password of a user in the database.

    Args:
        email (EmailStr): The email of the user.
        old_password (str): The old password of the user.
        new_password (str): The new password to be set.

    Raises:
        HTTPException: If the user with the email is not found or old password is incorrect.
        Exception: If there is an error with the database.

    Returns:
        dict: A JSON response with a success message.
    """
    user_id=current_user.user_id
    try:
        stmt = select(UserModel).where(UserModel.user_id == user_id, UserModel.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or not verify_password(old_password, user.password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        user.password = get_password_hash(new_password)
        await db.commit()
        return {"message": "User password updated successfully"}
    except Exception as e:
        await db.rollback()
        return error_response(message=str(e))

