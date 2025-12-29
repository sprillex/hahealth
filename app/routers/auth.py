from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app import database, models, schemas, auth
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    logger.info(f"Login attempt for user: {form_data.username}")

    user = db.query(models.User).filter(models.User.name == form_data.username).first()

    if not user:
        logger.warning(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth.verify_password(form_data.password, user.password_hash):
        logger.warning(f"Password verification failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Login successful for user: {form_data.username}")
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": user.name}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(refresh_token: str, db: Session = Depends(database.get_db)):
    """
    Exchange a valid refresh token for a new access token.
    """
    user = auth.verify_refresh_token(refresh_token, db)

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    # Ideally we might rotate the refresh token too, but for now we'll just return a new access token.
    # The response model requires a refresh_token, so we can return the same one or None if optional?
    # Schema says optional. Let's return the same one to be nice, or just let the client keep it?
    # If we don't return it, the client might overwrite their stored one with null if they aren't careful.
    # Best practice: return a NEW refresh token (rotation) or the SAME one.
    # Let's simple return the same one for now to avoid complexity of "family" invalidation logic.

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
