from agentscope.service import (
    create_file, ServiceResponse
)


def save_file(file_path: str, content: str = "") -> str | None:
    """
    save a file with the content.

    Args:
        file_path (`str`):
            The path where the file will be saved.
        content (`str`):
            Content to write into the file.

    Returns:
        `ServiceResponse`: Where the boolean indicates success, and the
        str contains an error message if any, including the error type.

    """
    create_file(file_path, content)
    return f"success save file {file_path}"
