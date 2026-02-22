from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth models ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserPublic(BaseModel):
    username: str
    email: EmailStr


class UserInDB(UserPublic):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# ── Generation models ─────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)
    negative_prompt: Optional[str] = Field(None, max_length=500)
    width: int = Field(512, ge=256, le=2048)
    height: int = Field(512, ge=256, le=2048)
    num_inference_steps: int = Field(30, ge=1, le=100)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)


class GenerateResponse(BaseModel):
    task_id: str
    status: str = "queued"
    message: str = "Image generation task has been queued successfully."


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
