import React from 'react';

interface Column<T> {
  header: React.ReactNode;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
}

export function Table<T extends { id?: string | number }>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No records found',
  className = '',
}: TableProps<T>) {
  return (
    <div className={`overflow-x-auto w-full border border-[#20293a] rounded-md bg-[#111620] ${className}`}>
      <table className="w-full text-left border-collapse text-xs tabular-nums">
        <thead>
          <tr className="border-b border-[#20293a] bg-[#141b26] text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
            {columns.map((col, idx) => (
              <th key={idx} className={`py-2.5 px-3 ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#18212e]">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-xs text-slate-500 font-mono">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr
                key={row.id || rowIdx}
                onClick={() => onRowClick && onRowClick(row)}
                className={`transition-colors duration-75 ${
                  onRowClick ? 'cursor-pointer hover:bg-[#182230]' : 'hover:bg-[#151c27]'
                }`}
              >
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className={`py-2.5 px-3 text-slate-300 ${col.className || ''}`}>
                    {col.cell ? col.cell(row) : col.accessorKey ? String(row[col.accessorKey] ?? '') : null}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
