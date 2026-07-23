from luxtj.contexts.customer.domain.enums import HolidayTypeEnum
from luxtj.contexts.customer.domain.errors import InvalidHolidayTypesError

MAX_HOLIDAY_TYPES_SELECTION = 3


def normalize_holiday_types(values: list[HolidayTypeEnum]) -> list[HolidayTypeEnum]:
    if len(values) > MAX_HOLIDAY_TYPES_SELECTION:
        raise InvalidHolidayTypesError(
            f"At most {MAX_HOLIDAY_TYPES_SELECTION} holiday types are allowed"
        )

    unique_values: list[HolidayTypeEnum] = []
    for value in values:
        if not isinstance(value, HolidayTypeEnum):
            raise InvalidHolidayTypesError(f"Invalid holiday type: {value!r}")
        if value not in unique_values:
            unique_values.append(value)

    if len(unique_values) != len(values):
        raise InvalidHolidayTypesError("Duplicate holiday types are not allowed")
    return unique_values


def supported_holiday_types() -> list[str]:
    return [item.value for item in HolidayTypeEnum]
