from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "USER"

    @field_validator("role")
    @classmethod
    def valid_role(cls, value):
        value = value.upper()
        if value not in {"USER", "IT_ADMIN"}:
            raise ValueError("Role must be USER or IT_ADMIN")
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

class RefreshRequest(BaseModel):
    refresh_token: str | None = None
