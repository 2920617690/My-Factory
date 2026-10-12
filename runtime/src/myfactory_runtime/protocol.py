"""Versioned execution envelopes; business context remains capability-specific."""
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')]
Version = Annotated[str, Field(pattern=r'^\d+\.\d+\.\d+$')]


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('UTC timestamp required')
    return value


class Envelope(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class EntityRef(Envelope):
    entity_id: Identifier
    entity_type: Identifier


class CapabilityRef(Envelope):
    capability_id: Identifier
    version: Version


class ContractRef(Envelope):
    contract_id: Identifier
    version: Version


class TaskRef(Envelope):
    task_id: Identifier
    status: Literal['CREATED','QUEUED','RUNNING','COMPLETED','FAILED','WAITING_APPROVAL','CANCELLED','INTERRUPTED']


class ExecutionRef(Envelope):
    execution_id: Identifier
    task_id: Identifier
    status: Literal['RUNNING','COMPLETED','FAILED']


class References(Envelope):
    task_id: Identifier
    execution_id: Identifier
    entity_id: Identifier | None = None
    trace_id: Identifier | None = None


class ExecutionPolicy(Envelope):
    mode: Literal['deterministic', 'brain'] = 'deterministic'
    read_only: bool = True
    timeout_seconds: Annotated[int, Field(ge=1, le=200)] = 180


class ExecutionRequest(Envelope):
    schema_version: Literal['mf.execution.v1'] = 'mf.execution.v1'
    task_id: Identifier
    execution_id: Identifier
    capability: CapabilityRef
    target: EntityRef
    context: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)


class ErrorEnvelope(Envelope):
    error_code: Identifier
    category: Literal['VALIDATION', 'NOT_FOUND', 'PERMISSION', 'PLUGIN_ERROR', 'RUNTIME_ERROR', 'INTERNAL']
    message: str
    refs: References
    details: dict[str, Any] = Field(default_factory=dict)


class TraceEntry(Envelope):
    trace_id: Identifier
    task_id: Identifier
    execution_id: Identifier
    entity_id: Identifier
    capability: CapabilityRef
    plugin_id: Identifier
    plugin_version: str
    start: str
    end: str | None = None
    status: Literal['RUNNING', 'COMPLETED', 'FAILED']
    result: Any = None
    error: ErrorEnvelope | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(Envelope):
    schema_version: Literal['mf.execution.v1'] = 'mf.execution.v1'
    task_id: Identifier
    execution_id: Identifier
    target: EntityRef
    status: Literal['COMPLETED', 'FAILED']
    output: Any = None
    state_effects: list[dict[str, Any]] = Field(default_factory=list)
    trace: list[TraceEntry]
    error: ErrorEnvelope | None = None


class ContractMeta(Envelope):
    contract_id: Identifier
    version: Version
    source: str
    generated_at: str

    @field_validator('generated_at')
    @classmethod
    def utc_timestamp(cls, value):
        return validate_utc(value)


class EventReferences(Envelope):
    entity_id: Identifier | None = None
    task_id: Identifier | None = None
    execution_id: Identifier | None = None


class EventEnvelope(Envelope):
    schema_version: Literal['mf.event.v1'] = 'mf.event.v1'
    event_id: Identifier
    event_type: Identifier
    timestamp_utc: str
    source: Identifier
    refs: EventReferences
    payload: dict[str, Any]

    @field_validator('timestamp_utc')
    @classmethod
    def utc_timestamp(cls,value):
        return validate_utc(value)
