from app.schemas.user_management import ViewUser
from app.db.session import get_db_session
from app.models.user import User as UserModel
from app.schemas.autentication import TokenData
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme) , db: AsyncSession = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},

    )
    token=credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
        token_data = TokenData(user_email=user_email)
         
        stmt=select(UserModel.user_id,UserModel.first_name,UserModel.last_name,UserModel.email).where(UserModel.email==token_data.user_email)
        result = await db.execute(stmt)
        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        db_user = result.first()
        if db_user is None:
            return {"error": "User not found"}
        user=ViewUser.from_orm(db_user)
        return user
    except jwt.DecodeError:
        raise credentials_exception