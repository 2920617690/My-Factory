import { Text } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'

import type { FactoryEntity } from '../types'

interface EquipmentMeshProps {
  entity: FactoryEntity
  selected: boolean
  onSelect: (entity: FactoryEntity) => void
}

export function EquipmentMesh({ entity, selected, onSelect }: EquipmentMeshProps) {
  const color = entity.status === 'idle' ? '#2f8f83' : '#c97335'

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    onSelect(entity)
  }

  return (
    <group position={[-2.2, 0.38, -0.9]} onClick={handleClick}>
      <mesh castShadow>
        <boxGeometry args={[1.4, 0.55, 0.9]} />
        <meshStandardMaterial color={selected ? '#f7b538' : color} metalness={0.18} roughness={0.45} />
      </mesh>
      <mesh position={[0.55, 0.42, 0]} castShadow>
        <cylinderGeometry args={[0.16, 0.16, 0.42, 24]} />
        <meshStandardMaterial color="#4f6670" metalness={0.2} roughness={0.35} />
      </mesh>
      <Text position={[0, 0.62, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.16} color="#172026">
        EQ-001
      </Text>
    </group>
  )
}

