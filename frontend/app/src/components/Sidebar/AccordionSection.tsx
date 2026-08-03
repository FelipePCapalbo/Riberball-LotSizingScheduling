import type { ReactNode } from 'react';

interface AccordionSectionProps {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export default function AccordionSection({ title, open, onToggle, children }: AccordionSectionProps) {
  return (
    <div className="sb-section">
      <button className="sb-section-toggle" onClick={onToggle}>
        {title}
        <svg className={`chevron${open ? '' : ' rotated'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="18 15 12 9 6 15" />
        </svg>
      </button>
      {open ? <div>{children}</div> : null}
    </div>
  );
}
