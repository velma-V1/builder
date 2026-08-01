// Structure-only placeholder — not installed, not run in this repository state.
// deck.gl overlay layered on top of MapView for high-density intelligence layers.
import { DeckGL } from "@deck.gl/react";
import { ScatterplotLayer } from "@deck.gl/layers";

export interface DeckOverlayProps {
  points: Array<{ position: [number, number]; weight: number }>;
  initialViewState: { longitude: number; latitude: number; zoom: number };
}

export function DeckOverlay({ points, initialViewState }: DeckOverlayProps): JSX.Element {
  const layers = [
    new ScatterplotLayer({
      id: "intelligence-points",
      data: points,
      getPosition: (d: (typeof points)[number]) => d.position,
      getRadius: (d: (typeof points)[number]) => 500 + d.weight * 100,
      getFillColor: [29, 78, 216, 160],
    }),
  ];
  return <DeckGL initialViewState={initialViewState} controller layers={layers} />;
}
