"""Application capability catalogue, not an Agent loop or plugin loader.

Providers adapt existing tools or small local services. Official Harness retains
its Cordis loading, guards and tool lifecycle on the brain execution path.
"""
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4
from .errors import RuntimeFault, sanitize
from .protocol import CapabilityRef, Envelope, TraceEntry, utc_now


class PluginManifest(Envelope):
    plugin_id: str
    version: str
    capabilities: list[CapabilityRef]
    runtime_requirements: dict[str, str]
    license_metadata: dict[str, str]


@dataclass(frozen=True)
class Provider:
    manifest: PluginManifest
    invoke: Callable


class ExecutionTrace:
    def __init__(self, request):
        self.request, self.entries = request, []

    def start(self, capability, plugin_id, version, attributes=None):
        r = self.request
        entry = TraceEntry(trace_id='TRACE-'+uuid4().hex, task_id=r.task_id, execution_id=r.execution_id,
            entity_id=r.target.entity_id, capability=capability, plugin_id=plugin_id, plugin_version=version,
            start=utc_now(), status='RUNNING', attributes=sanitize(attributes or {}))
        self.entries.append(entry)
        return entry

    def finish(self, entry, output=None, error=None):
        entry.end = utc_now()
        entry.status = 'FAILED' if error else 'COMPLETED'
        entry.result = sanitize(output)
        entry.error = error


class PluginRegistry:
    def __init__(self):
        self._plugins, self._capabilities = {}, {}

    def register(self, manifest, invoke):
        manifest = PluginManifest.model_validate(manifest).model_copy(deep=True)
        plugin_key = (manifest.plugin_id, manifest.version)
        keys = [(c.capability_id, c.version) for c in manifest.capabilities]
        if not keys or len(keys) != len(set(keys)) or plugin_key in self._plugins or any(k in self._capabilities for k in keys):
            raise RuntimeFault('REGISTRATION_CONFLICT', 'VALIDATION', '插件或能力版本已注册，注册未生效')
        provider = Provider(manifest, invoke)
        self._plugins[plugin_key] = provider
        for key in keys:
            self._capabilities[key] = provider

        def dispose():
            if self._plugins.pop(plugin_key, None) is provider:
                for key in keys:
                    self._capabilities.pop(key, None)
        return dispose

    def discover(self):
        return [CapabilityRef(capability_id=name, version=version).model_dump() for name, version in sorted(self._capabilities)]

    def manifests(self):
        return [p.manifest.model_dump() for p in self._plugins.values()]

    def resolve(self, capability):
        provider = self._capabilities.get((capability.capability_id, capability.version))
        if provider is None:
            exists = any(k[0] == capability.capability_id for k in self._capabilities)
            raise RuntimeFault('CAPABILITY_VERSION_NOT_FOUND' if exists else 'CAPABILITY_NOT_FOUND', 'NOT_FOUND', '未找到指定能力或版本')
        return provider

    def invoke(self, capability, request, trace, payload=None):
        provider = self.resolve(capability)
        entry = trace.start(capability, provider.manifest.plugin_id, provider.manifest.version)
        try:
            output = provider.invoke(capability.capability_id, request, trace, payload)
            trace.finish(entry, output)
            return output
        except RuntimeFault as fault:
            trace.finish(entry, error=fault.envelope(request, entry.trace_id))
            raise
        except Exception as error:
            fault = RuntimeFault('PLUGIN_INVOCATION_FAILED', 'PLUGIN_ERROR', '插件执行失败', {'exception_type': type(error).__name__})
            trace.finish(entry, error=fault.envelope(request, entry.trace_id))
            raise fault from error
