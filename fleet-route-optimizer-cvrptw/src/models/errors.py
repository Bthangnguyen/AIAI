from enum import Enum

class ErrorCode(str, Enum):
    NO_FEASIBLE_ROUTE = "NO_FEASIBLE_ROUTE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TOO_MANY_LOCKED = "TOO_MANY_LOCKED"
    OSRM_UNREACHABLE = "OSRM_UNREACHABLE"
    LLM_EXTRACTION_FAILED = "LLM_EXTRACTION_FAILED"
    LLM_PARSE_ERROR = "LLM_PARSE_ERROR"

class SolverException(Exception):
    def __init__(self, error_code: ErrorCode, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
