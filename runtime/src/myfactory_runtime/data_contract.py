"""Small versioned JSON Schema service. No remote schema fetching or code eval."""
from copy import deepcopy
from threading import RLock
from pydantic import ValidationError
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from .errors import RuntimeFault
from .protocol import ContractMeta, ContractRef


def local_references(value):
    if isinstance(value, dict):
        for key in ('$ref','$dynamicRef','$recursiveRef'):
            if key in value and not str(value[key]).startswith('#'):
                raise RuntimeFault('REMOTE_SCHEMA_REF_FORBIDDEN', 'PERMISSION', '本阶段契约仅支持本地引用')
        for v in value.values(): local_references(v)
    elif isinstance(value, list):
        for v in value: local_references(v)


class DataContracts:
    def __init__(self):
        self._contracts, self._transforms = {}, {}
        self._lock = RLock()

    def register(self, metadata, schema):
        try:
            meta = ContractMeta.model_validate(metadata)
        except ValidationError as error:
            raise RuntimeFault('CONTRACT_METADATA_INVALID','VALIDATION','契约元数据无效') from error
        local_references(schema)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise RuntimeFault('INVALID_CONTRACT_SCHEMA', 'VALIDATION', 'JSON Schema 无效') from error
        key = (meta.contract_id, meta.version)
        with self._lock:
            if key in self._contracts:
                raise RuntimeFault('CONTRACT_ALREADY_REGISTERED', 'VALIDATION', '该契约版本已注册')
            self._contracts[key] = (meta, Draft202012Validator(deepcopy(schema), format_checker=FormatChecker()))
        return meta.model_dump()

    def resolve_version(self, contract_id, requested_version):
        row = self._contracts.get((contract_id, requested_version))
        if row is None:
            raise RuntimeFault('CONTRACT_VERSION_NOT_FOUND', 'NOT_FOUND', '未找到契约或指定版本')
        return row[0].model_dump()

    def validate(self, contract_id, payload, version):
        meta = self.resolve_version(contract_id, version)
        validator = self._contracts[(contract_id, version)][1]
        try:
            errors = sorted(validator.iter_errors(payload), key=lambda e: str(list(e.path)))
        except Exception as error:
            raise RuntimeFault('CONTRACT_VALIDATION_FAILED', 'VALIDATION', '契约引用或校验失败') from error
        if errors:
            raise RuntimeFault('PAYLOAD_INVALID', 'VALIDATION', '数据不符合契约',
                {'fields': [{'path':list(e.path), 'rule':e.validator} for e in errors[:10]]})
        return {'valid':True, 'contract':meta}

    def register_transform(self, source, target, transform):
        self.resolve_version(*source)
        self.resolve_version(*target)
        key = (*source, *target)
        if key in self._transforms:
            raise RuntimeFault('TRANSFORM_ALREADY_REGISTERED', 'VALIDATION', '转换已注册')
        self._transforms[key] = transform

    def transform(self, source_contract, target_contract, payload):
        try:
            s = ContractRef.model_validate(source_contract)
            t = ContractRef.model_validate(target_contract)
        except ValidationError as error:
            raise RuntimeFault('CONTRACT_REFERENCE_INVALID','VALIDATION','契约引用无效') from error
        source, target = (s.contract_id,s.version), (t.contract_id,t.version)
        self.validate(source[0], payload, source[1])
        self.resolve_version(*target)
        if source == target:
            output = deepcopy(payload)
        else:
            handler = self._transforms.get((*source, *target))
            if handler is None:
                raise RuntimeFault('TRANSFORM_NOT_FOUND', 'NOT_FOUND', '没有匹配的数据转换')
            try:
                output = handler(deepcopy(payload))
            except Exception as error:
                raise RuntimeFault('TRANSFORM_FAILED', 'PLUGIN_ERROR', '数据转换失败') from error
        self.validate(target[0], output, target[1])
        return {'data':output, 'contract':self.resolve_version(*target)}

    def invoke(self, capability, request, trace, payload):
        if payload is None and request.policy.mode != 'deterministic':
            raise RuntimeFault('MODE_NOT_SUPPORTED', 'VALIDATION', '数据契约能力使用确定性执行')
        args = payload if payload is not None else request.parameters
        try:
            if capability == 'data_contract.register': return self.register(args['metadata'], args['schema'])
            if capability == 'data_contract.validate': return self.validate(args['contract_id'], args['payload'], args['version'])
            if capability == 'data_contract.resolve_version': return self.resolve_version(args['contract_id'], args['requested_version'])
            if capability == 'data_contract.transform': return self.transform(args['source_contract'], args['target_contract'], args['payload'])
        except KeyError as error:
            raise RuntimeFault('CONTRACT_ARGUMENT_MISSING', 'VALIDATION', '数据契约参数缺失', {'field':str(error)}) from error
        raise RuntimeFault('CAPABILITY_NOT_FOUND', 'NOT_FOUND', '未找到数据契约能力')
