// AutoPrism - Glass Card Component
import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { clsx } from 'clsx';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  opacity?: number;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export function GlassCard({
  children,
  className,
  opacity = 0.08,
  onClick,
  style,
}: GlassCardProps) {
  return (
    <motion.div
      className={clsx('glass', className)}
      style={{ background: `rgba(255,255,255,${opacity})`, ...style }}
      onClick={onClick}
    >
      {children}
    </motion.div>
  );
}

// Button variants
interface ButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit';
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  className,
  disabled,
  type = 'button',
}: ButtonProps) {
  const baseStyles = 'rounded-lg font-medium transition-all duration-200 flex items-center gap-2';
  const variants = {
    primary: 'bg-autoprism-purple text-white hover:bg-violet-600 shadow-[0_0_20px_rgba(139,92,246,0.4)]',
    secondary: 'bg-white/5 border border-white/10 text-white hover:bg-white/12',
    ghost: 'bg-transparent text-white/70 hover:text-white hover:bg-white/8',
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(baseStyles, variants[variant], sizes[size], disabled && 'opacity-50 cursor-not-allowed', className)}
    >
      {children}
    </button>
  );
}

// Input
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm text-white/70">{label}</label>}
      <input
        className={clsx(
          'px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/30',
          'focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30',
          'transition-all duration-200',
          error && 'border-red-500/50',
          className
        )}
        {...props}
      />
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}