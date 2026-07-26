import type { ReactNode } from 'react';
import { X } from 'lucide-react';

import { IconButton } from './Button';

export function Drawer({
  eyebrow,
  title,
  onClose,
  children,
  wide = false,
}: {
  eyebrow: ReactNode;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        aria-label={title}
        className={`drawer ${wide ? 'drawer-wide' : ''}`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="drawer-header">
          <div>
            <span className="eyebrow">{eyebrow}</span>
            <h2>{title}</h2>
          </div>
          <IconButton aria-label="关闭抽屉" onClick={onClose}>
            <X size={18} />
          </IconButton>
        </div>
        {children}
      </aside>
    </div>
  );
}
