from pydantic import BaseModel, Field

class SystemSettingRequest(BaseModel):
    value: str = Field(max_length=500)
