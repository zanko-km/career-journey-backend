from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    type: str
    message: str

    isRead: bool = Field(alias="is_read")

    referenceType: str | None = Field(
        default=None,
        alias="reference_type",
    )

    referenceId: int | None = Field(
        default=None,
        alias="reference_id",
    )

    createdAt: datetime = Field(
        alias="created_at",
    )

    readAt: datetime | None = Field(
        default=None,
        alias="read_at",
    )