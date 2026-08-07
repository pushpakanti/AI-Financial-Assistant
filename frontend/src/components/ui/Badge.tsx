import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'primary', className = '', ...props }) => {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold';
  
  const variants = {
    primary: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-200/50 dark:border-indigo-800/30',
    secondary: 'bg-slate-100 text-slate-700 dark:bg-slate-800/50 dark:text-slate-300 border border-slate-200/50 dark:border-slate-800/30',
    success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-200/50 dark:border-emerald-800/30',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200/50 dark:border-amber-800/30',
    danger: 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300 border border-rose-200/50 dark:border-rose-800/30',
    info: 'bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300 border border-sky-200/50 dark:border-sky-800/30',
  };

  return (
    <span className={`${baseStyles} ${variants[variant]} ${className}`} {...props}>
      {children}
    </span>
  );
};
export default Badge;
