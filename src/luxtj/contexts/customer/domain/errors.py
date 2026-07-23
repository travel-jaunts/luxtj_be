class CustomerBucketListError(Exception):
    pass


class BucketListItemAlreadyExistsError(CustomerBucketListError):
    pass


class BucketListItemNotFoundError(CustomerBucketListError):
    pass


class InvalidIdealDaysError(CustomerBucketListError):
    pass


class CustomerPersonalCalendarError(Exception):
    pass


class InvalidPersonalCalendarEventError(CustomerPersonalCalendarError):
    pass


class InvalidHolidayTypesError(CustomerPersonalCalendarError):
    pass


class InvalidPeriodDateRangeError(CustomerPersonalCalendarError):
    pass


class PersonalCalendarEventItemNotFoundError(CustomerPersonalCalendarError):
    pass


class PersonalCalendarPeriodItemNotFoundError(CustomerPersonalCalendarError):
    pass
