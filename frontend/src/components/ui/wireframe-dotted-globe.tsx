"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface RotatingEarthProps {
  width?: number;
  height?: number;
  className?: string;
  focusLat?: number;
  focusLng?: number;
  zoom?: number;
  points?: {
    id: string;
    lat: number;
    lng: number;
    intensity?: number;
    color?: string;
    label?: string;
    showLabel?: boolean;
  }[];
  autoRotate?: boolean;
  hoveredId?: string | null;
  selectedId?: string | null;
  onHover?: (id: string | null) => void;
  onSelect?: (id: string | null) => void;
}

export default function RotatingEarth({
  width = 800,
  height = 600,
  className = "",
  focusLat,
  focusLng,
  zoom = 1,
  points = [],
  autoRotate = false,
  hoveredId = null,
  selectedId = null,
  onHover,
  onSelect,
}: RotatingEarthProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hitPointsRef = useRef<
    { id: string; x: number; y: number; r: number }[]
  >([]);
  const renderRef = useRef<(() => void) | null>(null);
  const hoveredIdRef = useRef<string | null>(null);
  const selectedIdRef = useRef<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState({ width, height });

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const observer = new ResizeObserver(() => {
      const rect = container.getBoundingClientRect();
      setSize({
        width: Math.max(320, rect.width),
        height: Math.max(320, rect.height),
      });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    if (!context) return;

    const containerWidth = Math.min(size.width, window.innerWidth - 40);
    const containerHeight = Math.min(size.height, window.innerHeight - 100);
    const radius = Math.min(containerWidth, containerHeight) / 2.5;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;
    context.scale(dpr, dpr);

    const projection = d3
      .geoOrthographic()
      .scale(radius * zoom)
      .translate([containerWidth / 2, containerHeight / 2])
      .clipAngle(90);

    const path = d3.geoPath().projection(projection).context(context);

    const pointInPolygon = (point: [number, number], polygon: number[][]) => {
      const [x, y] = point;
      let inside = false;

      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i];
        const [xj, yj] = polygon[j];

        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
          inside = !inside;
        }
      }

      return inside;
    };

    const pointInFeature = (point: [number, number], feature: any) => {
      const geometry = feature.geometry;

      if (geometry.type === "Polygon") {
        const coordinates = geometry.coordinates;
        if (!pointInPolygon(point, coordinates[0])) {
          return false;
        }
        for (let i = 1; i < coordinates.length; i++) {
          if (pointInPolygon(point, coordinates[i])) {
            return false;
          }
        }
        return true;
      }
      if (geometry.type === "MultiPolygon") {
        for (const polygon of geometry.coordinates) {
          if (pointInPolygon(point, polygon[0])) {
            let inHole = false;
            for (let i = 1; i < polygon.length; i++) {
              if (pointInPolygon(point, polygon[i])) {
                inHole = true;
                break;
              }
            }
            if (!inHole) {
              return true;
            }
          }
        }
      }

      return false;
    };

    const generateDotsInPolygon = (feature: any, dotSpacing = 16) => {
      const dots: [number, number][] = [];
      const bounds = d3.geoBounds(feature);
      const [[minLng, minLat], [maxLng, maxLat]] = bounds;

      const stepSize = dotSpacing * 0.08;

      for (let lng = minLng; lng <= maxLng; lng += stepSize) {
        for (let lat = minLat; lat <= maxLat; lat += stepSize) {
          const point: [number, number] = [lng, lat];
          if (pointInFeature(point, feature)) {
            dots.push(point);
          }
        }
      }

      return dots;
    };

    interface DotData {
      lng: number;
      lat: number;
      visible: boolean;
    }

    const allDots: DotData[] = [];
    let landFeatures: any;

    const render = () => {
      context.clearRect(0, 0, containerWidth, containerHeight);

      const currentScale = projection.scale();
      const scaleFactor = currentScale / radius;

      context.beginPath();
      context.arc(
        containerWidth / 2,
        containerHeight / 2,
        currentScale,
        0,
        2 * Math.PI
      );
      context.fillStyle = "#0a0a0b";
      context.fill();
      context.strokeStyle = "#ffffff";
      context.lineWidth = 2 * scaleFactor;
      context.stroke();

      if (landFeatures) {
        hitPointsRef.current = [];
        const graticule = d3.geoGraticule();
        context.beginPath();
        path(graticule());
        context.strokeStyle = "#ffffff";
        context.lineWidth = 1.2 * scaleFactor;
        context.globalAlpha = 0.28;
        context.stroke();
        context.globalAlpha = 1;

        context.beginPath();
        landFeatures.features.forEach((feature: any) => {
          path(feature);
        });
        context.fillStyle = "rgba(255, 255, 255, 0.035)";
        context.fill();
        context.strokeStyle = "rgba(255, 255, 255, 0.6)";
        context.lineWidth = 1.4 * scaleFactor;
        context.stroke();

        allDots.forEach((dot) => {
          const projected = projection([dot.lng, dot.lat]);
          if (
            projected &&
            projected[0] >= 0 &&
            projected[0] <= containerWidth &&
            projected[1] >= 0 &&
            projected[1] <= containerHeight
          ) {
            context.beginPath();
            context.arc(projected[0], projected[1], 1.1 * scaleFactor, 0, 2 * Math.PI);
            context.fillStyle = "#9ca3af";
            context.fill();
          }
        });

        points.forEach((point) => {
          const projected = projection([point.lng, point.lat]);
          if (
            projected &&
            projected[0] >= 0 &&
            projected[0] <= containerWidth &&
            projected[1] >= 0 &&
            projected[1] <= containerHeight
          ) {
            const intensity = Math.max(0.2, Math.min(1, point.intensity ?? 0.6));
            const radius =
              (point.id === selectedIdRef.current ? 9 : 6) + intensity * 6;
            context.beginPath();
            context.arc(projected[0], projected[1], radius, 0, 2 * Math.PI);
            context.fillStyle = point.color ?? "rgba(239, 68, 68, 0.85)";
            context.fill();

            hitPointsRef.current.push({
              id: point.id,
              x: projected[0],
              y: projected[1],
              r: radius + 3,
            });

            if (
              point.label &&
              (point.showLabel ||
                point.id === hoveredIdRef.current ||
                point.id === selectedIdRef.current)
            ) {
              context.font = "600 13px Inter, system-ui, sans-serif";
              context.fillStyle = "#f3f4f6";
              context.fillText(
                point.label,
                projected[0] + radius + 6,
                projected[1] - radius - 4
              );
            }
          }
        });
      }
    };
    renderRef.current = render;

    const loadWorldData = async () => {
      try {
        setIsLoading(true);

        const response = await fetch(
          "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/physical/ne_110m_land.json"
        );
        if (!response.ok) throw new Error("Failed to load land data");

        landFeatures = await response.json();

        landFeatures.features.forEach((feature: any) => {
          const dots = generateDotsInPolygon(feature, 16);
          dots.forEach(([lng, lat]) => {
            allDots.push({ lng, lat, visible: true });
          });
        });

        render();
        setIsLoading(false);
      } catch (err) {
        setError("Failed to load land map data");
        setIsLoading(false);
      }
    };

    const rotation = [
      focusLng !== undefined ? -focusLng : 0,
      focusLat !== undefined ? -focusLat : 0,
    ];
    let shouldRotate = autoRotate;
    const rotationSpeed = 0.5;

    const rotate = () => {
      if (shouldRotate) {
        rotation[0] += rotationSpeed;
        projection.rotate(rotation);
        render();
      }
    };

    const rotationTimer = d3.timer(rotate);

    const handleMouseDown = (event: MouseEvent) => {
      shouldRotate = false;
      const startX = event.clientX;
      const startY = event.clientY;
      const startRotation = [...rotation];

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const sensitivity = 0.5;
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;

        rotation[0] = startRotation[0] + dx * sensitivity;
        rotation[1] = startRotation[1] - dy * sensitivity;
        rotation[1] = Math.max(-90, Math.min(90, rotation[1]));

        projection.rotate(rotation);
        render();
      };

      const handleMouseUp = () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);

        setTimeout(() => {
          shouldRotate = autoRotate;
        }, 10);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    };

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const scaleFactor = event.deltaY > 0 ? 0.9 : 1.1;
      const newRadius = Math.max(
        radius * 0.5,
        Math.min(radius * 3, projection.scale() * scaleFactor)
      );
      projection.scale(newRadius);
      render();
    };

    const handleMouseMove = (event: MouseEvent) => {
      if (!onHover) return;
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const hit = hitPointsRef.current.find(
        (point) => Math.hypot(point.x - x, point.y - y) <= point.r
      );
      onHover(hit?.id ?? null);
    };

    const handleMouseLeave = () => onHover?.(null);

    const handleClick = (event: MouseEvent) => {
      if (!onSelect) return;
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const hit = hitPointsRef.current.find(
        (point) => Math.hypot(point.x - x, point.y - y) <= point.r
      );
      onSelect(hit?.id ?? null);
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("wheel", handleWheel);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseleave", handleMouseLeave);
    canvas.addEventListener("click", handleClick);

    projection.rotate(rotation);
    loadWorldData();

    return () => {
      rotationTimer.stop();
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("wheel", handleWheel);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
      canvas.removeEventListener("click", handleClick);
    };
  }, [
    width,
    height,
    focusLat,
    focusLng,
    autoRotate,
    onHover,
    onSelect,
    points,
    size.height,
    size.width,
    zoom,
  ]);

  useEffect(() => {
    hoveredIdRef.current = hoveredId;
    selectedIdRef.current = selectedId;
    renderRef.current?.();
  }, [hoveredId, selectedId]);

  if (error) {
    return (
      <div className={`dark flex items-center justify-center bg-card rounded-2xl p-8 ${className}`}>
        <div className="text-center">
          <p className="dark text-destructive font-semibold mb-2">
            Error loading Earth visualization
          </p>
          <p className="dark text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
          Loading globe...
        </div>
      )}
      <canvas
        ref={canvasRef}
        className="w-full h-auto rounded-2xl bg-background dark"
        style={{ maxWidth: "100%", height: "auto" }}
      />
      <div className="absolute bottom-4 left-4 text-xs text-muted-foreground px-2 py-1 rounded-md dark bg-neutral-900">
        Drag to rotate • Scroll to zoom
      </div>
    </div>
  );
}
