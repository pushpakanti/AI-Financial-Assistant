import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glass?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, glass = true, className = '', ...props }) => {
  return (
    <div
      className={`rounded-2xl p-6 ${
        glass
          ? 'glass-card'
          : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm'
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => {
  return (
    <div className={`flex items-center justify-between mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({ children, className = '', ...props }) => {
  return (
    <h3 className={`text-base font-bold text-slate-800 dark:text-slate-100 ${className}`} {...props}>
      {children}
    </h3>
  );
};

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => {
  return <div className={className} {...props}>{children}</div>;
};

export default Card;
