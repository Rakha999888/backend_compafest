class DatasetNotFoundError(Exception):
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset with ID '{dataset_id}' not found")


class InvalidTransactionDataError(Exception):
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Invalid transaction data: {errors}")


class FileProcessingError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MLServiceError(Exception):
    def __init__(self, error_code: str, message: str, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"ML Service error [{error_code}]: {message}")


ML_ERROR_HTTP_STATUS = {
    "INVALID_INPUT": 400,
    "UNKNOWN_CATEGORY": 422,
    "EMPTY_ORDERS": 400,
    "ML_SERVICE_UNAVAILABLE": 503,
    "ML_SERVICE_TIMEOUT": 504,
    "ML_UNKNOWN_ERROR": 500,
}


def map_ml_error_to_http_status(error_code: str) -> int:
    return ML_ERROR_HTTP_STATUS.get(error_code, 500)