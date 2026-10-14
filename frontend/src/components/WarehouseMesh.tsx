import { Text } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'

import type { FactoryEntity } from '../types'

interface WarehouseMeshProps {
  entity: FactoryEntity
  selected: boolean
  onSelect: (entity: FactoryEntity) => void
}

export function WarehouseMesh({ entity, selected, onSelect }: WarehouseMeshProps) {
  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation()
    onSelect(entity)
  }

  return (
    <group position={[1.75, 0.42, -0.8]} onClick={handleClick}>
      <mesh castShadow>
        <boxGeometry args={[1.45, 0.8, 1.1]} />
        <meshStandardMaterial color={selected ? '#f7b538' : '#3b6ea8'} roughness={0.48} />
      </mesh>
      {[0, 1, 2].map((index) => (
        <mesh key={index} position={[-0.46 + index * 0.46, 0.52, 0.62]} castShadow>
          <boxGeometry args={[0.32, 0.22, 0.28]} />
          <meshStandardMaterial color="#d79c43" roughness={0.5} />
        </mesh>
      ))}
      <Text position={[0, 0.86, 0]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.16} color="#172026">
        WH-001
      </Text>
    </group>
  )
}

