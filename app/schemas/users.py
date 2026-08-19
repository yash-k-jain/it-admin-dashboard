from pydantic import BaseModel, EmailStr, Field

class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)

class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None
    name: str | None = Field(default=None, max_length=100)

class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
