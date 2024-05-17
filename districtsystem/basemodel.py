import uuid

from pydantic import UUID4, BaseModel, Field


class BaseEquipment(BaseModel):
    bldg_id: UUID4 = Field(default_factory=uuid.uuid4, description="The unique id of the equipment")
