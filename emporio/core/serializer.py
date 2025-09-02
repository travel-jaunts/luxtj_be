from pydantic import BaseModel

from emporio.common.utils import to_camel_case


class BaseSerializer(BaseModel):
    """
    Base serializer class that can be extended by other serializers.
    It provides a common structure for all serializers in the application.
    """

    class Config:
        # Use snake_case for field names in the serialized output
        alias_generator = to_camel_case
        populate_by_name = True
        use_enum_values = True
