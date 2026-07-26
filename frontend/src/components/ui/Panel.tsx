import type { HTMLAttributes, ReactNode } from 'react';

interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  as?: 'article' | 'section' | 'div';
}

export function Panel({ children, as: Tag = 'section', className = '', ...props }: PanelProps) {
  return (
    <Tag className={`surface-panel ${className}`.trim()} {...props}>
      {children}
    </Tag>
  );
}

export function PanelHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="surface-panel-heading">
      <div>
        {eyebrow && <span className="panel-key">{eyebrow}</span>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}
