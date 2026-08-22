from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.models.user import User


async def notify_employee(
    db: AsyncSession,
    employee_id: int,
    type: str,
    message: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> Notification | None:
    """Create a notification for the User linked to the given employee_id.

    If the employee has no provisioned User row yet (e.g. auth not set up),
    this silently does nothing rather than failing the calling request.
    """
    result = await db.execute(
        select(User.id).where(User.employee_id == employee_id)
    )
    user_id = result.scalar_one_or_none()

    if user_id is None:
        return None

    notification = Notification(
        user_id=user_id,
        type=type,
        message=message,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(notification)
    return notification
