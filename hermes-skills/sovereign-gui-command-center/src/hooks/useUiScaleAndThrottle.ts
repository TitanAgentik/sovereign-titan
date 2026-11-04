import { useEffect, useRef, useState } from 'react';

/**
 * Provides global UI Zoom controls (Ctrl + - / Ctrl + = / Ctrl + 0)
 * and throttles high-frequency 120Hz IPC telemetry to 10Hz for React DOM text
 * so panels never jitter while canvases stay at 120 FPS.
 */
export function useGlobalUiScale(defaultScale = 0.85) {
  const [scale, setScale] = useState<number>(() => {
    const saved = localStorage.getItem('titan_ui_scale');
    return saved ? parseFloat(saved) : defaultScale;
  });

  useEffect(() => {
    const clamped = Math.min(1.25, Math.max(0.55, Number(scale.toFixed(2))));
    document.documentElement.style.setProperty('--ui-scale', String(clamped));
    document.documentElement.style.fontSize = `${(11 * clamped).toFixed(2)}px`;
    localStorage.setItem('titan_ui_scale', String(clamped));
  }, [scale]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          setScale((s) => Math.max(0.55, Number((s - 0.05).toFixed(2))));
        } else if (e.key === '=' || e.key === '+') {
          e.preventDefault();
          setScale((s) => Math.min(1.25, Number((s + 0.05).toFixed(2))));
        } else if (e.key === '0') {
          e.preventDefault();
          setScale(0.85);
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return { scale, setScale };
}

export function useThrottledValue<T>(value: T, intervalMs = 100): T {
  const [throttled, setThrottled] = useState<T>(value);
  const latestRef = useRef<T>(value);
  latestRef.current = value;

  useEffect(() => {
    const id = setInterval(() => {
      setThrottled(latestRef.current);
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return throttled;
}
