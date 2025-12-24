from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import secrets
import hashlib

# Secret key for JWT. In production, this should be in environment variables.
SECRET_KEY = "your-secret-key-please-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
api_key_header = APIKeyHeader(name="X-Webhook-Secret", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.name == username).first()
    if user is None:
        raise credentials_exception
    return user

def generate_api_key():
    raw_key = secrets.token_urlsafe(32)
    return raw_key

def hash_api_key(api_key: str):
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_webhook_api_key(api_key: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    hashed = hash_api_key(api_key)
    # Check if key exists and is active.
    # Since we need to know WHICH user this is associated with to log data against them,
    # the webhook architecture needs to handle user identification.
    # The plan says "The Home Assistant webhook requires a Shared Secret Key...".
    # It doesn't explicitly say the key maps to a user, but "All tables include user_id".
    # So the key MUST map to a user.

    key_record = db.query(models.APIKey).filter(models.APIKey.hashed_key == hashed, models.APIKey.is_active == True).first()
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return key_record.user
