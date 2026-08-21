import React from 'react';

/**
 * Official Tamil Nadu Government Seal (தமிழ்நாடு அரசு சின்னம்).
 * Uses the authentic vector Seal_of_Tamil_Nadu.svg from the public assets.
 */
export default function TnEmblem({ size = 44, className = '', opacity = 1, style = {} }) {
  const pixelSize = typeof size === 'number' ? `${size}px` : size;

  return (
    <img
      src="/Seal_of_Tamil_Nadu.svg"
      alt="Tamil Nadu Government Official Seal"
      width={size}
      height={size}
      className={className}
      style={{
        width: pixelSize,
        height: pixelSize,
        objectFit: 'contain',
        opacity,
        display: 'inline-block',
        flexShrink: 0,
        ...style,
      }}
      loading="eager"
    />
  );
}
