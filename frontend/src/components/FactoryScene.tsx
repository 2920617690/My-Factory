import { ContactShadows, Grid, OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'

import type { FactoryEntity, FloorFilter } from '../types'
import { FloorLayer } from './FloorLayer'

interface FactorySceneProps {
  visibleFloor: FloorFilter
  entities: FactoryEntity[]
  selectedEntityId: string
  onSelectEntity: (entity: FactoryEntity) => void
  resetKey: number
}

export function FactoryScene({
  visibleFloor,
  entities,
  selectedEntityId,
  onSelectEntity,
  resetKey,
}: FactorySceneProps) {
  const visibleFloors = visibleFloor === 'all' ? (['F1', 'F2'] as const) : [visibleFloor]

  return (
    <Canvas
      key={resetKey}
      camera={{ position: [6.2, 4.3, 5.8], fov: 42 }}
      shadows
      onPointerMissed={() => {
        const factory = entities.find((entity) => entity.id === 'FACTORY-001')
        if (factory) onSelectEntity(factory)
      }}
    >
      <color attach="background" args={['#eef3f1']} />
      <ambientLight intensity={0.85} />
      <directionalLight position={[3.6, 6, 4.2]} intensity={1.65} castShadow />
      <group position={[0, -0.05, 0]}>
        {visibleFloors.map((floor) => (
          <FloorLayer
            key={floor}
            floor={floor}
            entities={entities.filter((entity) => entity.floor === floor)}
            selectedEntityId={selectedEntityId}
            onSelectEntity={onSelectEntity}
          />
        ))}
      </group>
      <Grid
        position={[0, -0.08, 0]}
        args={[8, 8]}
        cellSize={0.5}
        cellThickness={0.7}
        sectionSize={2}
        sectionThickness={1.1}
        cellColor="#a7b8b2"
        sectionColor="#71857d"
        fadeDistance={16}
        fadeStrength={1}
      />
      <ContactShadows position={[0, -0.04, 0]} opacity={0.25} scale={8} blur={2.5} />
      <OrbitControls makeDefault target={[0, 0.7, 0]} enableDamping minDistance={3.8} maxDistance={10} />
    </Canvas>
  )
}

