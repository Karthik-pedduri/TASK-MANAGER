from pydantic import BaseModel, EmailStr, field_validator
from app.utils.sanitization import sanitize_string


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

    @field_validator("username", "full_name", mode="before")
    @classmethod
    def sanitize(cls, v):
        return sanitize_string(v)


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None


class UserResponse(UserBase):
    user_id: int

    class Config:
        from_attributes = True
