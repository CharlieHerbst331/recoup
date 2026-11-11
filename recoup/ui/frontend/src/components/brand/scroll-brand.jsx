import { useEffect, useState } from "react";
import { RAMP_SYMBOL, RAMP_WORDMARK } from "./brand-paths";
import "./scroll-brand.css";

// Adapted from the user-supplied logo-scroll-sandbox; original SVG paths retained.
export function ScrollBrand({ brand = "recoup", forceState, onClick, disabled = false }) {
  const [progress, setProgress] = useState(0);
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (forceState) return;
    let frame = 0;
    const read = () => {
      setProgress(Math.min(1, Math.max(0, (window.scrollY - 24) / 120)));
      frame = 0;
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(read);
    };
    read();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, [forceState]);
  const p = forceState
    ? Number(forceState === "collapsed")
    : reduced ? Number(progress > 0.5) : progress;
  const markX = 112 * (1 - p);
  return (
    <a
      href="#"
      aria-label={`${brand === "ramp" ? "Ramp" : "Recoup"} home`}
      aria-disabled={disabled || undefined}
      onClick={(event) => {
        event.preventDefault();
        if (!disabled) onClick?.();
      }}
      className="scroll-brand"
      data-state={p === 0 ? "expanded" : p === 1 ? "collapsed" : "transitioning"}
      style={{ width: markX + 38 }}
    >
      <span
        aria-hidden="true"
        className="brand-word"
        style={{ width: 104 * (1 - p), opacity: Math.max(0, 1 - p * 1.6), transform: `translateX(${-10 * p}px)` }}
      >
        {brand === "ramp" ? (
          <svg width="104" height="42" viewBox="0 0 269 110" fill="currentColor"><path d={RAMP_WORDMARK} /></svg>
        ) : <span className="recoup-word">recoup</span>}
      </span>
      <svg aria-hidden="true" className="brand-symbol" width="38" height="42" viewBox="284 0 101 110" fill="currentColor" style={{ transform: `translateX(${markX}px)` }}>
        <path d={RAMP_SYMBOL} />
      </svg>
    </a>
  );
}
