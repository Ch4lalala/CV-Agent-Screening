from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.common import OrmResponse


class UserCreate(BaseModel):
    email: EmailStr
    password_hash: str = Field(min_length=1, max_length=255, repr=False)
    full_name: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1, max_length=255, repr=False)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "UserUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class UserResponse(OrmResponse):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
    updated_at: datetime

