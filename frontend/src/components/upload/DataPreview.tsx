import { useSessionStore } from "../../stores/useSessionStore";

export default function DataPreview() {
  const { columns, preview, rowCount, colCount, fileName } = useSessionStore();

  if (!preview.length) return null;

  return (
    <div className="mb-6">
      <div className="flex items-baseline gap-3 mb-2">
        <h3 className="text-sm font-semibold text-slate-600">
          {fileName}
        </h3>
        <span className="text-xs text-slate-400">
          {rowCount.toLocaleString()} rows × {colCount} columns
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-xs">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left font-semibold text-slate-600 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                {columns.map((col) => (
                  <td
                    key={col}
                    className="px-3 py-1.5 text-slate-700 whitespace-nowrap"
                  >
                    {row[col] == null ? (
                      <span className="text-slate-300">—</span>
                    ) : (
                      String(row[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
