import React from 'react';

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  headerBorder?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  headerBorder = true,
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`bg-[#131923] border border-[#222b3b] rounded-md transition-colors overflow-hidden ${className}`}
      {...props}
    >
      {(title || subtitle || action) && (
        <div
          className={`px-4 py-3 flex items-center justify-between gap-4 ${
            headerBorder ? 'border-b border-[#1d2634]' : ''
          }`}
        >
          <div>
            {title && (
              <h3 className="text-xs font-semibold text-slate-100 uppercase tracking-wider font-mono">
                {title}
              </h3>
            )}
            {subtitle && <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
};
