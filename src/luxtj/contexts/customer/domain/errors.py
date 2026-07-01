class CustomerBucketListError(Exception):
    pass


class BucketListItemAlreadyExistsError(CustomerBucketListError):
    pass


class BucketListItemNotFoundError(CustomerBucketListError):
    pass


class InvalidIdealDaysError(CustomerBucketListError):
    pass
