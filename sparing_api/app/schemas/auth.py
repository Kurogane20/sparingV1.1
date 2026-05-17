import re
from pydantic import BaseModel, EmailStr, field_validator

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password harus mengandung huruf kapital')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password harus mengandung angka')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ('admin', 'operator', 'viewer'):
            raise ValueError('Role tidak valid')
        return v

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    site_uids: list[str] = []
