import logging
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from ..core.database import get_db
from ..core.config import get_settings
from ..core.security import get_password_hash, verify_password, create_access_token, get_current_user
from ..models.user import User, UserRole

logger = logging.getLogger("laptop_allocation.auth")

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
_optional_oauth_scheme = OAuth2PasswordBearer(tokenUrl="", auto_error=False)


def _optional_current_user(
    token: Optional[str] = Depends(_optional_oauth_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.STAFF


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: int

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    full_name: str


class RegisterResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: Optional[User] = Depends(_optional_current_user),
):
    if user_data.role == UserRole.ADMIN and not admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to create an admin account",
        )
    if admin_user and admin_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to create an admin account",
        )

    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    username = form_data.username
    logger.info("Login attempt for username=%r", username)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning("Login failed for username=%r: user not found", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning("Login failed for username=%r: invalid password", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        logger.warning("Login blocked for username=%r: account inactive", username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    logger.info("Login succeeded for username=%r (id=%s, role=%s)", username, user.id, user.role.value)
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role.value,
        username=user.username,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
