import type { ReactNode } from 'react';

export interface TabItem {
  key: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  activeKey: string;
  onChange: (key: string) => void;
  variant: 'main' | 'sub';
}

export default function Tabs({ tabs, activeKey, onChange, variant }: TabsProps) {
  const navClassName = variant === 'main' ? 'nav nav-tabs main-tabs' : 'nav nav-tabs sub-tabs mt-3';

  return (
    <>
      <ul className={navClassName} role="tablist">
        {tabs.map((tab) => (
          <li className="nav-item" key={tab.key}>
            <button
              className={tab.key === activeKey ? 'nav-link active' : 'nav-link'}
              onClick={() => onChange(tab.key)}
            >
              {tab.label}
            </button>
          </li>
        ))}
      </ul>
      <div className={variant === 'main' ? 'tab-content main-tab-content' : 'tab-content'}>
        {tabs.map((tab) =>
          tab.key === activeKey ? (
            <div className="tab-pane fade show active" key={tab.key}>
              {tab.content}
            </div>
          ) : null,
        )}
      </div>
    </>
  );
}
