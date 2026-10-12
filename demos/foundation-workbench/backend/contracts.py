"""Versioned projections for mock business state and independent simulation state."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Quantity = Annotated[int, Field(strict=True, ge=0)]


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Provenance(Record):
    source_system: str
    source_record_id: str
    observed_at: datetime
    mapping_version: Literal['foundation.mapping.v1'] = 'foundation.mapping.v1'


class Material(Record):
    material_id: str
    name: str
    unit: Literal['piece', 'set']
    source_unit: str
    provenance: Provenance


class Inventory(Record):
    material_id: str
    on_hand: Quantity
    reserved: Quantity
    quality_hold: Quantity
    available: Quantity
    version: Annotated[int, Field(strict=True, ge=1)]
    floor_available: dict[str, Quantity]
    provenance: list[Provenance]

    @model_validator(mode='after')
    def net_quantity(self):
        if self.available != self.on_hand - self.reserved - self.quality_hold:
            raise ValueError('Net availability differs from stock, reservations and holds')
        if sum(self.floor_available.values()) != self.available:
            raise ValueError('Floor availability differs from plant availability')
        return self


class BomLine(Record):
    material_id: str
    per_unit: Annotated[int, Field(strict=True, ge=1)]


class Order(Record):
    order_id: str
    product: str
    quantity: Quantity
    target_floor: Literal[1, 2]
    line_id: str
    due_at: datetime
    priority: str
    bom: list[BomLine]
    provenance: Provenance


class Location(Record):
    location_id: str
    name: str
    floor: Literal[1, 2]


class FactoryState(Record):
    schema_version: Literal['foundation.factory-state.v1'] = 'foundation.factory-state.v1'
    factory_id: Literal['FACTORY-001'] = 'FACTORY-001'
    factory_name: str
    timezone: Literal['Asia/Shanghai'] = 'Asia/Shanghai'
    data_mode: Literal['mock'] = 'mock'
    state_domain: Literal['business_view'] = 'business_view'
    authority: Literal['temporary_mock_seed'] = 'temporary_mock_seed'
    snapshot_id: str
    as_of: datetime
    revision: Annotated[int, Field(strict=True, ge=1)]
    seed_sha256: str
    materials: list[Material]
    inventory: list[Inventory]
    orders: list[Order]
    locations: list[Location]
    equipment: list[dict] = Field(default_factory=list)

    @model_validator(mode='after')
    def entity_ids(self):
        ids = [row.material_id for row in self.materials]
        if len(set(ids)) != len(ids) or set(ids) != {row.material_id for row in self.inventory}:
            raise ValueError('Material and inventory IDs do not match')
        if len(self.inventory) != len(ids):
            raise ValueError('Duplicate inventory ID')
        if any(line.material_id not in ids for order in self.orders for line in order.bom):
            raise ValueError('Unknown BOM material')
        return self


class BrainSubmission(Record):
    task_id: str = Field(pattern=r'^FDN-[a-f0-9]{32}$')
    snapshot_id: str
    order_id: str | None = None
    order_ids: list[str] | None = Field(default=None, min_length=2, max_length=5)
    question: str = Field(min_length=1, max_length=1600)

    @model_validator(mode='after')
    def selection(self):
        if (self.order_id is None) == (self.order_ids is None):
            raise ValueError('Choose one order or an order group')
        if self.order_ids is not None:
            if len(set(self.order_ids)) != len(self.order_ids):
                raise ValueError('Duplicate order IDs')
            self.order_ids = sorted(self.order_ids)
        return self


class SimulationRequest(Record):
    """C creates its own run; business inventory is never an output destination."""
    scenario_id: str
    strategy: Literal['baseline', 'replenish']


class SimulationState(Record):
    schema_version: Literal['foundation.simulation-state.v1'] = 'foundation.simulation-state.v1'
    state_domain: Literal['simulation'] = 'simulation'
    run_id: str
    scenario_id: str
    clock_unit: Literal['minute'] = 'minute'
    sim_time: Annotated[float, Field(ge=0)]
    inventory: dict[str, Quantity]
    equipment: dict[str, str] = Field(default_factory=dict)
