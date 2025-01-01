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
from app.models.user import User as UserModel
from app.schemas.user_management import PaginatedUserResponse, ViewUser

user_router = APIRouter()
add_pagination(user_router)

@user_router.get("/users/{user_mail}")
async def read_users(user_mail: EmailStr, db: AsyncSession = Depends(get_db_session)):
    """Returns a list of all user objects in the database."""
    try:
        stmt = select(UserModel).where(UserModel.email == user_mail)
        result = await db.execute(stmt)
        users = result.scalars().all()

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
        total_users_query = select(func.count(UserModel.id))
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar()
        total_pages = ceil(total_users/size)
        if page > total_pages:
            raise HTTPException(status_code=404, detail="Page not found")
        users_query = select(
               UserModel.id, UserModel.user_id, UserModel.first_name, UserModel.last_name, UserModel.email
               )
        users = await db.execute(users_query.limit(size).offset((page-1)*size))
        return PaginatedUserResponse(users= [ViewUser.from_orm(user) for user in users], total_users=total_users, total_pages=total_pages, current_page=page, has_next=page < total_pages, has_previous=page > 1)
    
    except Exception as e:
        return error_response(message=str(e))
