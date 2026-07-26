import type { ReactNode } from 'react';

export type StatusTone = 'ok' | 'warning' | 'danger' | 'neutral' | 'info';

export function Status({
  tone = 'neutral',
  children,
}: {
  tone?: StatusTone;
  children: ReactNode;
}) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}
