"""Composition root is the only module importing concrete providers."""
import json
import shutil
from pathlib import Path
from .adapter import MyFactoryRuntimeAdapter
from .data_contract import DataContracts
from .harness import OfficialHarnessAdapter
from .plugins import InventoryPlugin, EquipmentPlugin
from .registry import PluginRegistry

ROOT = Path(__file__).resolve().parents[2]


def manifest(plugin_id, version, capabilities, runtime):
    return {'plugin_id':plugin_id,'version':version,
            'capabilities':[{'capability_id':c,'version':'1.0.0'} for c in capabilities],
            'runtime_requirements':{'provider':runtime},
            'license_metadata':{'spdx':'MIT','review':'development_scope_only'}}


def create_runtime(config_path=None):
    path = Path(config_path) if config_path else ROOT/'config/runtime.local.json'
    if config_path is None and not path.is_file():
        path = ROOT/'config/runtime.example.json'
    config = json.loads(path.read_text())
    registry, contracts = PluginRegistry(), DataContracts()
    definitions = json.loads((ROOT/'fixtures/mock-contracts.json').read_text())
    for row in definitions:
        contracts.register(row['metadata'],row['schema'])
    source = ('mf.mock.factory-context','0.1.0')
    target = ('mf.mock.factory-context','1.0.0')
    contracts.register_transform(source,target,lambda old:{**{k:v for k,v in old.items() if k!='state'},'factory_state':old['state']})
    registry.register(manifest('mf.data-contract','0.1.0',[
        'data_contract.register','data_contract.validate','data_contract.transform','data_contract.resolve_version'], 'python-jsonschema'), contracts.invoke)
    node = config.get('node_binary') or shutil.which('node')
    harness = OfficialHarnessAdapter(config.get('harness',{}),ROOT/'fixtures/factory-scenarios.json',ROOT/'evidence/raw')
    inventory = InventoryPlugin(registry,node,ROOT/'plugins/poc-inventory/invoke.mjs',harness)
    registry.register(manifest('mf.inventory.mock','0.3.0',['inventory.analyze'],'poc-pure-js / official-cordis-tools'),inventory.invoke)
    equipment = EquipmentPlugin()
    registry.register(manifest('mf.equipment.mock','0.1.0',['equipment.inspect'],'python-mock'),equipment.invoke)
    return MyFactoryRuntimeAdapter(registry)
