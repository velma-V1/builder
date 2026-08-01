// MapLibre wrapper for the Map Intelligence Center / WorldMonitor Workspace templates.
import { useEffect, useRef, type JSX } from "react";
import { Map as MapLibreGLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export interface MapViewProps {
  center: [number, number];
  zoom: number;
  styleUrl?: string;
}

export function MapView({ center, zoom, styleUrl = "https://demotiles.maplibre.org/style.json" }: MapViewProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreGLMap | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = new MapLibreGLMap({
      container: containerRef.current,
      style: styleUrl,
      center,
      zoom,
    });
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={containerRef} style={{ height: 480, width: "100%" }} />;
}
