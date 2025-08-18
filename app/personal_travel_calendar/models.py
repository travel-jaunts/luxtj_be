from datetime import date
from enum import StrEnum

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import CheckConstraint

from app.core.datastore import BaseModel


class HolidayThemePreference(StrEnum):
    pass




class UserPersonalTravelCalendar(BaseModel):
    """
    Model for storing personal travel calendar details.
    This model can be extended to include additional fields as needed.
    """

    user_id: Mapped[int] = mapped_column(primary_key=True)
    ocassion_type: Mapped[str] = mapped_column(
        nullable=False, index=True, comment="Type of the occasion"
    )
    is_date_range: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Indicates if the occasion is a date range"
    )
    start_date: Mapped[date] = mapped_column(
        nullable=False, comment="Start date of the occasion"
    )
    end_date: Mapped[date] = mapped_column(
        nullable=True, comment="End date of the occasion (if applicable)"
    )
    holiday_mood_preference: Mapped[str] = mapped_column(
        nullable=False, comment="User's mood preferences for holiday",
        default=[] # Default to an empty list if no preferences are set
    )
    holiday_theme_preference: Mapped[HolidayThemePreference] = mapped_column(
        nullable=False, comment="User's theme preferences for holiday",
        default=[]
    )
    __table_args__ = (
        CheckConstraint(
            "(is_date_range OR end_date = start_date)",
            name="check_end_date_equals_start_date_if_not_range"
        ),
    )
