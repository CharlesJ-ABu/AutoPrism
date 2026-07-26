import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  wide?: boolean;
  children: ReactNode;
}

export function Button({
  variant = 'secondary',
  wide = false,
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`${variant}-button${wide ? ' wide' : ''} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}

export function IconButton({
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`icon-button ${className}`.trim()} {...props} />;
}
