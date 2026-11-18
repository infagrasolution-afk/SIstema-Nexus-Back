from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    tenant_id: int


class Login(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TOTPVerifyRequest(BaseModel):
    code: str
    password: Optional[str] = None
