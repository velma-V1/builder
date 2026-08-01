// Structure-only placeholder — not installed, not run in this repository state.
// A 3D ambient status orb (3D Orb Interface template). `state` is backend-sourced — the orb's
// visual reflects it, it never decides system state on its own.
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Mesh } from "three";

export type OrbState = "idle" | "working" | "attention" | "error";

const COLOR_BY_STATE: Record<OrbState, string> = {
  idle: "#6b7280",
  working: "#1d4ed8",
  attention: "#d97706",
  error: "#dc2626",
};

export interface OrbProps {
  state: OrbState;
}

export function Orb({ state }: OrbProps): JSX.Element {
  const meshRef = useRef<Mesh>(null);

  useFrame((_frameState, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * (state === "working" ? 0.6 : 0.15);
    }
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshStandardMaterial color={COLOR_BY_STATE[state]} roughness={0.3} metalness={0.4} />
    </mesh>
  );
}
