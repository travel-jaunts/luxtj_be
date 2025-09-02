def to_camel_case(string_obj: str) -> str:
    """
    Convert a string to camelCase.

    Args:
        string_obj (str): The string to convert.

    Returns:
        str: The camelCase version of the input string.
    """
    parts = string_obj.split("_")
    return (
        parts[0] + "".join(part.capitalize() for part in parts[1:])
        if parts
        else string_obj
    )
