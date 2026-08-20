import React from 'react';

/**
 * Tamil Nadu Government Emblem — Inline SVG component.
 * Used in sidebar header and as watermark on empty states.
 */
export default function TnEmblem({ size = 40, className = '', opacity = 1 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ opacity }}
    >
      {/* Outer circle */}
      <circle cx="100" cy="100" r="95" stroke="currentColor" strokeWidth="3" fill="none" />
      <circle cx="100" cy="100" r="88" stroke="currentColor" strokeWidth="1.5" fill="none" />

      {/* Ashoka Chakra - center wheel */}
      <circle cx="100" cy="78" r="22" stroke="currentColor" strokeWidth="2.5" fill="none" />
      {/* 24 spokes */}
      {Array.from({ length: 24 }).map((_, i) => {
        const angle = (i * 15 * Math.PI) / 180;
        const x1 = 100 + 10 * Math.cos(angle);
        const y1 = 78 + 10 * Math.sin(angle);
        const x2 = 100 + 21 * Math.cos(angle);
        const y2 = 78 + 21 * Math.sin(angle);
        return (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1" />
        );
      })}
      <circle cx="100" cy="78" r="5" fill="currentColor" />

      {/* Lion Capital - stylized */}
      {/* Base platform */}
      <rect x="72" y="50" width="56" height="4" rx="2" fill="currentColor" />
      <rect x="78" y="46" width="44" height="4" rx="2" fill="currentColor" />

      {/* Lions (simplified silhouette) */}
      <path
        d="M85 46 L85 30 C85 24 90 20 95 20 L105 20 C110 20 115 24 115 30 L115 46"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
      />
      {/* Lion heads */}
      <circle cx="90" cy="22" r="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
      <circle cx="110" cy="22" r="6" stroke="currentColor" strokeWidth="1.5" fill="none" />

      {/* Bull and Horse base */}
      <line x1="72" y1="54" x2="128" y2="54" stroke="currentColor" strokeWidth="1.5" />

      {/* "சத்தியமேவ ஜயதே" - Satyameva Jayate in Tamil */}
      <text
        x="100"
        y="120"
        textAnchor="middle"
        fontSize="9"
        fontFamily="'Noto Sans Tamil', sans-serif"
        fill="currentColor"
        fontWeight="600"
      >
        சத்தியமேவ ஜயதே
      </text>

      {/* Government of Tamil Nadu text */}
      <text
        x="100"
        y="140"
        textAnchor="middle"
        fontSize="8"
        fontFamily="'Noto Sans Tamil', sans-serif"
        fill="currentColor"
        fontWeight="500"
      >
        தமிழ்நாடு அரசு
      </text>

      {/* Erode District */}
      <text
        x="100"
        y="155"
        textAnchor="middle"
        fontSize="10"
        fontFamily="'Noto Sans Tamil', sans-serif"
        fill="currentColor"
        fontWeight="700"
      >
        ஈரோடு மாவட்டம்
      </text>

      {/* Decorative border dots */}
      {Array.from({ length: 36 }).map((_, i) => {
        const angle = (i * 10 * Math.PI) / 180;
        const x = 100 + 92 * Math.cos(angle);
        const y = 100 + 92 * Math.sin(angle);
        return <circle key={`dot-${i}`} cx={x} cy={y} r="1.5" fill="currentColor" />;
      })}
    </svg>
  );
}
