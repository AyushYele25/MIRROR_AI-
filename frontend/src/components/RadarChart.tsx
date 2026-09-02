"use client";

import React from "react";
import { FeatureVector } from "../lib/api";

interface RadarChartProps {
  vector: FeatureVector;
  size?: number;
}

const DIMENSIONS: { key: keyof FeatureVector; label: string }[] = [
  { key: "code_quality", label: "Code Quality" },
  { key: "testing", label: "Testing" },
  { key: "architecture", label: "Architecture" },
  { key: "documentation", label: "Docs" },
  { key: "iteration", label: "Iteration" },
  { key: "debugging", label: "Debugging" },
  { key: "tooling", label: "Tooling" },
  { key: "ml_workflow", label: "ML Workflow" },
];

export const RadarChart: React.FC<RadarChartProps> = ({ vector, size = 360 }) => {
  const center = size / 2;
  const radius = (size / 2) * 0.72;
  const numPoints = DIMENSIONS.length;
  const angleStep = (Math.PI * 2) / numPoints;

  // Concentric levels (20, 40, 60, 80, 100)
  const levels = [0.2, 0.4, 0.6, 0.8, 1.0];

  // Calculate polygon vertices for data
  const dataPoints = DIMENSIONS.map((dim, i) => {
    const value = Math.max(5, Math.min(100, vector[dim.key] || 0));
    const normalized = value / 100;
    const angle = i * angleStep - Math.PI / 2;
    const x = center + radius * normalized * Math.cos(angle);
    const y = center + radius * normalized * Math.sin(angle);
    return { x, y, value, label: dim.label };
  });

  const polygonPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";

  return (
    <div className="relative flex flex-col items-center justify-center p-2">
      <svg width={size} height={size} className="overflow-visible">
        <defs>
          <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.45" />
            <stop offset="60%" stopColor="#8b5cf6" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.05" />
          </radialGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Concentric grid rings */}
        {levels.map((lvl, idx) => {
          const r = radius * lvl;
          return (
            <circle
              key={idx}
              cx={center}
              cy={center}
              r={r}
              fill="none"
              stroke="rgba(148, 163, 184, 0.15)"
              strokeDasharray={idx === levels.length - 1 ? undefined : "3 3"}
              strokeWidth="1"
            />
          );
        })}

        {/* Axis rays */}
        {DIMENSIONS.map((_, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const x2 = center + radius * Math.cos(angle);
          const y2 = center + radius * Math.sin(angle);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={x2}
              y2={y2}
              stroke="rgba(148, 163, 184, 0.2)"
              strokeWidth="1"
            />
          );
        })}

        {/* Data polygon */}
        <path
          d={polygonPath}
          fill="url(#radarGradient)"
          stroke="#06b6d4"
          strokeWidth="2.5"
          filter="url(#glow)"
        />

        {/* Data points */}
        {dataPoints.map((pt, i) => (
          <g key={i}>
            <circle
              cx={pt.x}
              cy={pt.y}
              r="4.5"
              fill="#06b6d4"
              stroke="#0f172a"
              strokeWidth="2"
              className="transition-transform hover:scale-150 cursor-pointer"
            />
          </g>
        ))}

        {/* Dimension Labels */}
        {DIMENSIONS.map((dim, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const labelRadius = radius + 24;
          const x = center + labelRadius * Math.cos(angle);
          const y = center + labelRadius * Math.sin(angle);
          const val = Math.round(vector[dim.key] || 0);

          return (
            <text
              key={i}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[11px] font-medium fill-slate-300 select-none"
            >
              {dim.label} <tspan className="fill-cyan-400 font-bold">{val}</tspan>
            </text>
          );
        })}
      </svg>
    </div>
  );
};
