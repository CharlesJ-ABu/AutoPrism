// AutoPrism - 3D Nebula Background
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import type { TechTag } from '@/types';

interface NebulaBackgroundProps {
  tags: TechTag[];
  opacity?: number;
}

// Individual star particle with depth and cool colors
function StarField() {
  const ref = useRef<THREE.Points>(null);
  const count = 3000;

  const { positions, colors } = useMemo(() => {
    const posArr = new Float32Array(count * 3);
    const colArr = new Float32Array(count * 3);
    const colorOptions = [new THREE.Color('#ffffff'), new THREE.Color('#818CF8'), new THREE.Color('#38BDF8')];

    for (let i = 0; i < count; i++) {
      posArr[i * 3] = (Math.random() - 0.5) * 60;
      posArr[i * 3 + 1] = (Math.random() - 0.5) * 60;
      posArr[i * 3 + 2] = (Math.random() - 0.5) * 60;

      const mixedColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
      colArr[i * 3] = mixedColor.r;
      colArr[i * 3 + 1] = mixedColor.g;
      colArr[i * 3 + 2] = mixedColor.b;
    }
    return { positions: posArr, colors: colArr };
  }, []);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.elapsedTime * 0.015;
      ref.current.rotation.x = state.clock.elapsedTime * 0.008;
    }
  });

  return (
    <Points ref={ref} positions={positions} colors={colors} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        vertexColors
        size={0.08}
        sizeAttenuation={true}
        depthWrite={false}
        opacity={0.8}
      />
    </Points>
  );
}

// Tech nodes with icons and text labels outside
function NebulaNodes({ tags }: { tags: TechTag[] }) {
  const ref = useRef<THREE.Group>(null);

  const nodes = useMemo(() => {
    return tags.map((tag, i) => {
      const angle = (i / tags.length) * Math.PI * 2;
      const radius = 6 + Math.random() * 8;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius * 0.5 + (Math.random() - 0.5) * 4;
      const z = Math.sin(angle) * radius * 0.4;

      let color = '#8B5CF6';
      if (tag.category === 'Infra') color = '#06B6D4';
      else if (tag.category === 'Web3') color = '#F59E0B';

      return {
        ...tag,
        position: [x, y, z] as [number, number, number],
        color,
        scale: Math.max(0.4, Math.min(1.8, tag.hotness / 100)),
      };
    });
  }, [tags]);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.elapsedTime * 0.03;
    }
  });

  return (
    <group ref={ref}>
      {nodes.map((node) => (
        <group key={node.id} position={node.position}>
          {/* Inner Glowing Core - Circle geometry for flat organic feel */}
          <mesh>
            <circleGeometry args={[node.scale * 0.4, 32]} />
            <meshBasicMaterial
              color={node.color}
              transparent
              opacity={0.3}
              side={THREE.DoubleSide}
            />
          </mesh>
          {/* Outer Wireframe Shell */}
          <mesh>
            <icosahedronGeometry args={[node.scale * 0.35, 1]} />
            <meshBasicMaterial
              color={node.color}
              wireframe
              transparent
              opacity={0.15}
            />
          </mesh>
        </group>
      ))}

      {/* High-tech connecting lines */}
      {nodes.slice(0, Math.min(nodes.length, 25)).map((node, i) => {
        const next = nodes[(i + 1) % Math.min(nodes.length, 25)];
        const points = [new THREE.Vector3(...node.position), new THREE.Vector3(...next.position)];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        return (
          <line key={`line-${i}`}>
            <bufferGeometry attach="geometry" {...geometry} />
            <lineBasicMaterial attach="material" color={node.color} transparent opacity={0.15} />
          </line>
        );
      })}
    </group>
  );
}

export function NebulaBackground({ tags, opacity = 0.4 }: NebulaBackgroundProps) {
  return (
    <div className="fixed inset-0 -z-10 bg-[#03030b]" style={{ opacity }}>
      <Canvas camera={{ position: [0, 0, 18], fov: 60 }}>
        <ambientLight intensity={0.5} />
        <StarField />
        {tags.length > 0 && <NebulaNodes tags={tags} />}

        {/* Post-processing Bloom for Glow Effect */}
        <EffectComposer>
          <Bloom
            luminanceThreshold={0.8}
            mipmapBlur
            intensity={0.3}
            radius={0.3}
          />
        </EffectComposer>

        {/* Deep space ambient sphere */}
        <mesh>
          <sphereGeometry args={[40, 32, 32]} />
          <meshBasicMaterial color="#0A0A1F" transparent opacity={0.4} side={THREE.BackSide} />
        </mesh>
      </Canvas>
    </div>
  );
}
