from datetime import datetime, timedelta, timezone
from jwt import encode as jwt_encode
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


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
