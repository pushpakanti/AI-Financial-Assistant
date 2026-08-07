import React from 'react';

interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
  headers: string[];
  children: React.ReactNode;
}

export const Table: React.FC<TableProps> = ({ headers, children, className = '', ...props }) => {
  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-200/50 dark:border-slate-800/50 bg-white/30 dark:bg-slate-900/10 backdrop-blur-sm">
      <table className={`w-full border-collapse text-left text-sm ${className}`} {...props}>
        <thead>
          <tr className="border-b border-slate-250/55 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/30">
            {headers.map((header, idx) => (
              <th
                key={idx}
                className="py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-150/60 dark:divide-slate-850/60 bg-transparent">
          {children}
        </tbody>
      </table>
    </div>
  );
};

export const TableRow: React.FC<React.HTMLAttributes<HTMLTableRowElement>> = ({ children, className = '', ...props }) => {
  return (
    <tr
      className={`hover:bg-slate-50/45 dark:hover:bg-slate-900/20 transition-colors ${className}`}
      {...props}
    >
      {children}
    </tr>
  );
};

export const TableCell: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({ children, className = '', ...props }) => {
  return (
    <td className={`py-3.5 px-4 font-normal text-slate-700 dark:text-slate-350 ${className}`} {...props}>
      {children}
    </td>
  );
};

export default Table;
