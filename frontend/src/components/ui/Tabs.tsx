import React from 'react';

interface TabOption {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

interface TabsProps {
  options: TabOption[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  options,
  activeTab,
  onChange,
  className = '',
}) => {
  return (
    <div className={`flex border-b border-slate-200 dark:border-slate-800 gap-1 overflow-x-auto ${className}`}>
      {options.map((option) => {
        const isActive = activeTab === option.id;
        return (
          <button
            key={option.id}
            onClick={() => onChange(option.id)}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-semibold border-b-2 transition-all duration-200 whitespace-nowrap -mb-px ${
              isActive
                ? 'border-indigo-600 text-indigo-650 dark:text-indigo-400 dark:border-indigo-500'
                : 'border-transparent text-slate-550 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:border-slate-200 dark:hover:border-slate-800'
            }`}
          >
            {option.icon && <span className="shrink-0">{option.icon}</span>}
            {option.label}
          </button>
        );
      })}
    </div>
  );
};
export default Tabs;
