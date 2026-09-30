import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'sm',
  isLoading = false,
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-md transition-colors duration-100 focus:outline-none focus:ring-1 focus:ring-slate-400 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none border';

  const sizeStyles = {
    xs: 'text-xs px-2 py-1 gap-1.5',
    sm: 'text-xs px-3 py-1.5 gap-2',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-sm px-4 py-2.5 gap-2.5',
  };

  const variantStyles = {
    primary: 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500 active:bg-blue-700 shadow-xs',
    secondary: 'bg-[#18212e] hover:bg-[#1f2b3c] text-slate-200 border-[#2b394e] active:bg-[#141b26]',
    outline: 'bg-transparent hover:bg-[#18212e] text-slate-300 border-[#2b394e] active:bg-[#141b26]',
    danger: 'bg-rose-950/80 hover:bg-rose-900 text-rose-200 border-rose-800/80 active:bg-rose-950',
    ghost: 'bg-transparent hover:bg-[#18212e] text-slate-400 hover:text-slate-200 border-transparent',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <svg className="animate-spin -ml-0.5 h-3.5 w-3.5 text-current" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      ) : (
        icon && <span className="shrink-0">{icon}</span>
      )}
      {children}
    </button>
  );
};
