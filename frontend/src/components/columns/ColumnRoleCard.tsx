import { useState } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { COLUMN_ROLES } from "../../types";
import AnnotationTrackOptions from "./AnnotationTrackOptions";

interface Props {
  col: string;
}

export default function ColumnRoleCard({ col }: Props) {
  const role = useSessionStore((s) => s.roles[col] ?? "Skip");
  const displayName = useSessionStore((s) => s.displayNames[col] ?? col);
  const setRole = useSessionStore((s) => s.setRole);
  const setDisplayName = useSessionStore((s) => s.setDisplayName);
  const dataRowCmaps = useSessionStore((s) => s.dataRowCmaps[col]);
  const setDataRowCmap = useSessionStore((s) => s.setDataRowCmap);

  const [open, setOpen] = useState(role !== "Skip");

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-3 py-2 flex items-center justify-between bg-white hover:bg-slate-50 text-left"
      >
        <span className="font-medium text-sm text-slate-800">{col}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            role === "Skip"
              ? "bg-slate-100 text-slate-400"
              : "bg-blue-100 text-blue-700"
          }`}
        >
          {role}
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-2 bg-slate-50/50">
          <label className="block">
            <span className="text-xs text-slate-500">Role</span>
            <select
              value={role}
              onChange={(e) => setRole(col, e.target.value)}
              className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
            >
              {COLUMN_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-slate-500">Display name</span>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(col, e.target.value)}
              className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
            />
          </label>

          {role === "Annotation Track" && (
            <AnnotationTrackOptions col={col} />
          )}

          {role === "Data Row" && (
            <label className="block">
              <span className="text-xs text-slate-500">Colormap</span>
              <select
                value={dataRowCmaps ?? "viridis"}
                onChange={(e) => setDataRowCmap(col, e.target.value)}
                className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
              >
                {[
                  "viridis", "plasma", "inferno", "magma",
                  "coolwarm", "RdBu", "YlOrRd", "Blues",
                ].map((cm) => (
                  <option key={cm}>{cm}</option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}
    </div>
  );
}
