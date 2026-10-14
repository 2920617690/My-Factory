import { Text } from '@react-three/drei'

import type { FactoryEntity, FloorId } from '../types'
import { EquipmentMesh } from './EquipmentMesh'
import { WarehouseMesh } from './WarehouseMesh'

interface FloorLayerProps {
  floor: FloorId
  entities: FactoryEntity[]
  selectedEntityId: string
  onSelectEntity: (entity: FactoryEntity) => void
}

const markerPositions: Record<string, [number, number, number]> = {
  'EQ-002': [-0.7, 0.32, -1.05],
  'AGV-001': [-0.85, 0.22, 0.75],
  'WS-001': [-1.55, 0.3, 0.35],
  'AGV-002': [1.55, 0.22, 0.78],
}

export function FloorLayer({ floor, entities, selectedEntityId, onSelectEntity }: FloorLayerProps) {
  const y = floor === 'F1' ? 0 : 1.45
  const floorColor = floor === 'F1' ? '#dbe7e4' : '#e7ddc9'
  const railColor = floor === 'F1' ? '#7c9a9a' : '#9a8a6a'
  const entityById = new Map(entities.map((entity) => [entity.id, entity]))
  const renderedIds = new Set(['EQ-001', 'WH-001', 'NODE-001', 'WS-002'])

  return (
    <group position={[0, y, 0]}>
      <mesh receiveShadow>
        <boxGeometry args={[6.2, 0.08, 3.8]} />
        <meshStandardMaterial color={floorColor} roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.07, 0]}>
        <boxGeometry args={[6.35, 0.06, 0.08]} />
        <meshStandardMaterial color={railColor} />
      </mesh>
      <mesh position={[0, 0.07, -1.9]}>
        <boxGeometry args={[6.35, 0.06, 0.08]} />
        <meshStandardMaterial color={railColor} />
      </mesh>
      <mesh position={[-3.1, 0.07, -0.95]}>
        <boxGeometry args={[0.08, 0.06, 1.9]} />
        <meshStandardMaterial color={railColor} />
      </mesh>
      <mesh position={[3.1, 0.07, -0.95]}>
        <boxGeometry args={[0.08, 0.06, 1.9]} />
        <meshStandardMaterial color={railColor} />
      </mesh>

      <Text position={[-2.85, 0.16, 1.45]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.22} color="#172026">
        {floor} 模拟厂区楼层
      </Text>

      {floor === 'F1' && entityById.get('EQ-001') && (
        <EquipmentMesh
          entity={entityById.get('EQ-001')!}
          selected={selectedEntityId === 'EQ-001'}
          onSelect={onSelectEntity}
        />
      )}
      {floor === 'F1' && entityById.get('WH-001') && (
        <WarehouseMesh
          entity={entityById.get('WH-001')!}
          selected={selectedEntityId === 'WH-001'}
          onSelect={onSelectEntity}
        />
      )}
      {floor === 'F1' && entityById.get('NODE-001') && (
        <LogisticsNode
          entity={entityById.get('NODE-001')!}
          selected={selectedEntityId === 'NODE-001'}
          onSelect={onSelectEntity}
        />
      )}
      {floor === 'F2' && entityById.get('WS-002') && (
        <Workstation
          entity={entityById.get('WS-002')!}
          selected={selectedEntityId === 'WS-002'}
          onSelect={onSelectEntity}
        />
      )}
      {entities
        .filter((entity) => !renderedIds.has(entity.id))
        .map((entity) => (
          <EntityMarker
            key={entity.id}
            entity={entity}
            selected={selectedEntityId === entity.id}
            onSelect={onSelectEntity}
          />
        ))}
    </group>
  )
}

interface EntityMeshProps {
  entity: FactoryEntity
  selected: boolean
  onSelect: (entity: FactoryEntity) => void
}

function LogisticsNode({ entity, selected, onSelect }: EntityMeshProps) {
  return (
    <group
      position={[0.15, 0.22, 0.95]}
      onClick={(event) => {
        event.stopPropagation()
        onSelect(entity)
      }}
    >
      <mesh castShadow>
        <cylinderGeometry args={[0.34, 0.34, 0.28, 32]} />
        <meshStandardMaterial color={selected ? '#f7b538' : '#7068a8'} roughness={0.4} />
      </mesh>
      <Text position={[0, 0.34, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.14} color="#172026">
        NODE-001
      </Text>
    </group>
  )
}

function Workstation({ entity, selected, onSelect }: EntityMeshProps) {
  return (
    <group
      position={[0.25, 0.32, -0.35]}
      onClick={(event) => {
        event.stopPropagation()
        onSelect(entity)
      }}
    >
      <mesh castShadow>
        <boxGeometry args={[1.65, 0.42, 1.2]} />
        <meshStandardMaterial color={selected ? '#f7b538' : '#8e6a4f'} roughness={0.52} />
      </mesh>
      <mesh position={[0, 0.34, 0.38]} castShadow>
        <boxGeometry args={[1.1, 0.22, 0.22]} />
        <meshStandardMaterial color="#547a74" />
      </mesh>
      <Text position={[0, 0.58, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.16} color="#172026">
        WS-002
      </Text>
    </group>
  )
}

function EntityMarker({ entity, selected, onSelect }: EntityMeshProps) {
  const position = markerPositions[entity.id] ?? [0, 0.28, 0]
  const color = entity.kind === 'agv' ? '#6f7fd8' : entity.kind === 'equipment' ? '#2f8f83' : '#8e6a4f'

  return (
    <group
      position={position}
      onClick={(event) => {
        event.stopPropagation()
        onSelect(entity)
      }}
    >
      <mesh castShadow>
        <boxGeometry args={entity.kind === 'agv' ? [0.72, 0.22, 0.42] : [0.78, 0.36, 0.58]} />
        <meshStandardMaterial color={selected ? '#f7b538' : color} roughness={0.46} />
      </mesh>
      <Text position={[0, 0.36, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.13} color="#172026">
        {entity.id}
      </Text>
    </group>
  )
}
