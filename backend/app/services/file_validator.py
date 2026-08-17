from typing import Optional

ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

MAX_FILE_SIZE = 10 * 1024 * 1024


class FileValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class FileValidator:

    @staticmethod
    def validate(filename: str, content_type: Optional[str], size: int) -> None:
        if size > MAX_FILE_SIZE:
            raise FileValidationError(
                f"File size {size} bytes exceeds maximum {MAX_FILE_SIZE} bytes (10MB)"
            )

        ext = ""
        dot_idx = filename.rfind(".")
        if dot_idx != -1:
            ext = filename[dot_idx:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"File extension '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
            )

        if content_type and content_type not in ALLOWED_MIME_TYPES:
            if ext == ".csv":
                pass
            else:
                raise FileValidationError(
                    f"MIME type '{content_type}' not allowed. Allowed: {ALLOWED_MIME_TYPES}"
                )
