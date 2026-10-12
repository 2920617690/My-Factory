"""Public errors omit stack traces, credentials and untrusted input echoes."""
import re
from .protocol import ErrorEnvelope, References


def sanitize(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if any(x in k.lower() for x in ('api_key', 'authorization', 'password', 'secret')) else sanitize(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return re.sub(r'sk-[A-Za-z0-9_-]{12,}', '[REDACTED]', value)
    return value


class RuntimeFault(Exception):
    def __init__(self, code, category, message, details=None):
        super().__init__(message)
        self.code, self.category, self.message = code, category, message
        self.details = details or {}

    def envelope(self, request, trace_id=None):
        return ErrorEnvelope(error_code=self.code, category=self.category, message=sanitize(self.message),
            refs=References(task_id=request.task_id, execution_id=request.execution_id,
                            entity_id=request.target.entity_id, trace_id=trace_id), details=sanitize(self.details))
