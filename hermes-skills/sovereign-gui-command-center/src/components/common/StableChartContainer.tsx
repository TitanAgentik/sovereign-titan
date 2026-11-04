import React, { useEffect, useRef } from 'react';

interface StableChartContainerProps {
  onResize?: (width: number, height: number) => void;
  children: React.ReactNode;
  className?: string;
}

/**
 * Kills ResizeObserver infinite loops in Flex/Grid layouts by isolating the canvas
 * inside an absolute-positioned inner mount and applying a 2px deadband + rAF guard.
 */
export const StableChartContainer: React.FC<StableChartContainerProps> = ({
  onResize,
  children,
  className = '',
}) => {
  const outerRef = useRef<HTMLDivElement | null>(null);
  const lastSize = useRef<{ w: number; h: number }>({ w: 0, h: 0 });

  useEffect(() => {
    const el = outerRef.current;
    if (!el || !onResize) return;

    let rafId: number | null = null;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      const nextW = Math.floor(rect.width);
      const nextH = Math.floor(rect.height);

      // 2-pixel deadband prevents sub-pixel flexbox oscillation loops
      if (
        Math.abs(nextW - lastSize.current.w) < 2 &&
        Math.abs(nextH - lastSize.current.h) < 2
      ) {
        return;
      }

      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        if (nextW > 10 && nextH > 10) {
          lastSize.current = { w: nextW, h: nextH };
          onResize(nextW, nextH);
        }
      });
    });

    ro.observe(el);
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      ro.disconnect();
    };
  }, [onResize]);

  return (
    <div ref={outerRef} className={`titan-canvas-lock ${className}`}>
      <div className="titan-canvas-inner">{children}</div>
    </div>
  );
};
