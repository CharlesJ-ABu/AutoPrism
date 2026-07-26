import type { ReactNode } from 'react';
import { AlertTriangle, LoaderCircle, Radar } from 'lucide-react';

import { Button } from './Button';

export function LoadingState({ label = '正在读取可信数据…' }: { label?: string }) {
  return (
    <div className="async-state" role="status">
      <LoaderCircle className="spin" size={22} />
      <strong>{label}</strong>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="async-state empty-state">
      <Radar size={24} />
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="async-state error-state" role="alert">
      <AlertTriangle size={22} />
      <strong>可信数据读取失败</strong>
      <p>{message}</p>
      {onRetry && <Button onClick={onRetry}>重试</Button>}
    </div>
  );
}
