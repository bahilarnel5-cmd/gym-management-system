from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class GymMemberCreate(BaseModel):
    organization_id: UUID
    member_code: str
    full_name: str
    email: Optional[str] = None
    mobile_phone: str
    assigned_coach_id: Optional[UUID] = None
    status: str = "active"
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None


class GymMemberUpdate(BaseModel):
    member_code: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    mobile_phone: Optional[str] = None
    assigned_coach_id: Optional[UUID] = None
    status: Optional[str] = None
    updated_by: Optional[UUID] = None


class GymMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    member_code: str
    full_name: str
    email: Optional[str]
    mobile_phone: str
    assigned_coach_id: Optional[UUID]
    status: str