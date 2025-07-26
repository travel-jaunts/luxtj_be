from typing import List
from enum import Enum

from app.core.serializer import BaseSerializer


class SpecialDayEnum(Enum):
    """
    Enum for special days.
    """

    MY_BIRTHDAY = "my_birthday", "My Birthday"
    MY_ANNIVERSARY = "my_anniversary", "My Anniversary"
    SPOUSE_BIRTHDAY = "spouse_birthday", "Spouse's Birthday"
    MOTHER_BIRTHDAY = "mother_birthday", "Mother's Birthday"
    FATHER_BIRTHDAY = "father_birthday", "Father's Birthday"
    CHILD_BIRTHDAY = "child_birthday", "Child's Birthday"


class SpecialDayDetail(BaseSerializer):
    """
    Serializer for special occasion details.
    """

    ocassion: str
    render_text: str


class DefaultOcassionsView(BaseSerializer):
    """
    Response Model for Personal Travel Calendar Details.
    """

    available_ocassions: List[SpecialDayDetail]

    @classmethod
    def get_defaults(cls) -> "DefaultOcassionsView":
        """
        Returns a default instance of PersonalTravelCalendarView with no occasions.
        """
        return cls(
            available_ocassions=[
                SpecialDayDetail(ocassion=k, render_text=str(v.value[1]))
                for k, v in SpecialDayEnum._member_map_.items()
            ]
        )


class HolidayPeriodEnum(Enum):
    """
    Enum for holiday breaks.
    """

    MY_WORK_BREAK = "my_work_break", "My Work Break"
    SPOUSE_WORK_BREAK = "spouse_work_break", "Spouse's Work Break"
    CHILD_VACATION = "child_vacation", "Child's Vacation Period"
    PARENT_AVAILABILITY = "parent_availability", "Parent's Availability"


class HolidayPeriodDetail(BaseSerializer):
    """
    Serializer for holiday break details.
    """

    break_type: str
    render_text: str


class DefaultBreaksView(BaseSerializer):
    """
    Response Model for default breaks.
    """

    available_breaks: List[HolidayPeriodDetail]

    @classmethod
    def get_defaults(cls) -> "DefaultBreaksView":
        """
        Returns a default instance of DefaultBreaksView with no breaks.
        """
        return cls(
            available_breaks=[
                HolidayPeriodDetail(break_type=k, render_text=str(v.value[1]))
                for k, v in HolidayPeriodEnum._member_map_.items()
            ]
        )


# Request Serializers ---------------------------------------------------------
