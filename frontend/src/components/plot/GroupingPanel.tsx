import { useSessionStore } from "../../stores/useSessionStore";

export default function GroupingPanel() {
  const columns = useSessionStore((s) => s.columns);
  const roles = useSessionStore((s) => s.roles);
  const groupColumns = useSessionStore((s) => s.groupColumns);
  const setGroupColumns = useSessionStore((s) => s.setGroupColumns);

  const sampleCol = Object.entries(roles).find(
    ([, r]) => r === "Sample ID"
  )?.[0];
  const geneCol = Object.entries(roles).find(
    ([, r]) => r === "Gene / Feature"
  )?.[0];
  const mutCol = Object.entries(roles).find(
    ([, r]) => r === "Mutation Type"
  )?.[0];

  const exclude = new Set(
    [sampleCol, geneCol, mutCol].filter(Boolean) as string[]
  );
  const groupable = columns.filter((c) => !exclude.has(c));

  const nLevels = groupColumns.length;

  const addLevel = () => {
    if (nLevels < 4) setGroupColumns([...groupColumns, ""]);
  };
  const removeLevel = () => {
    setGroupColumns(groupColumns.slice(0, -1));
  };
  const setLevel = (idx: number, col: string) => {
    const next = [...groupColumns];
    next[idx] = col;
    setGroupColumns(next);
  };

  const used = new Set(groupColumns.filter(Boolean));

  return (
    <div>
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
        Grouping
      </h2>
      <div className="space-y-2">
        {groupColumns.map((gc, i) => (
          <label key={i} className="block">
            <span className="text-xs text-slate-500">Level {i + 1}</span>
            <select
              value={gc}
              onChange={(e) => setLevel(i, e.target.value)}
              className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
            >
              <option value="">(None)</option>
              {groupable
                .filter((c) => c === gc || !used.has(c))
                .map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
            </select>
          </label>
        ))}
        <div className="flex gap-2">
          {nLevels < 4 && (
            <button
              onClick={addLevel}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              + Add level
            </button>
          )}
          {nLevels > 0 && (
            <button
              onClick={removeLevel}
              className="text-xs text-red-500 hover:text-red-700"
            >
              − Remove
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
