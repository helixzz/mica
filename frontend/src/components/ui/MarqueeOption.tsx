import React, { useEffect, useRef, useState } from 'react';

interface MarqueeOptionProps {
  children: React.ReactNode;
}

export function MarqueeOption({ children }: MarqueeOptionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [overflowPx, setOverflowPx] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      const diff = el.scrollWidth - el.clientWidth;
      setOverflowPx(diff > 2 ? diff : 0);
    };

    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(el);

    return () => observer.disconnect();
  }, [children]);

  return (
    <div
      ref={ref}
      className={overflowPx > 0 ? 'marquee-option marquee-option--overflow' : 'marquee-option'}
      style={{
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: overflowPx > 0 ? 'clip' : 'ellipsis',
        '--marquee-offset': `${-overflowPx}px`,
        '--marquee-duration': `${Math.max(2.5, overflowPx / 40 + 1.5)}s`,
      } as React.CSSProperties}
    >
      <span className="marquee-option__text">{children}</span>
    </div>
  );
}
