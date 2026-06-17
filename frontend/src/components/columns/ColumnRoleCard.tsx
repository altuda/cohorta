import { useState } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { COLUMN_ROLES } from "../../types";
import AnnotationTrackOptions from "./AnnotationTrackOptions";
import MutationColorsPanel from "../plot/MutationColorsPanel";

interface Props {
  col: string;
}

export default function ColumnRoleCard({ col }: Props) {
  const role = useSessionStore((s) => s.roles[col] ?? "Skip");
  const roles = useSessionStore((s) => s.roles);
  const displayName = useSessionStore((s) => s.displayNames[col] ?? col);
  const setRole = useSessionStore((s) => s.setRole);
  const setDisplayName = useSessionStore((s) => s.setDisplayName);

  const [open, setOpen] = useState(role !== "Skip");

  // Mutation/gene colours belong to the column that drives the matrix colours:
  // the Mutation Type column when present, else the Gene / Feature column
  // (gene-as-colour mode). Shown inline so all colours live with their column.
  const hasMutType = Object.values(roles).includes("Mutation Type");
  const showMutColors =
    role === "Mutation Type" ||
    (role === "Gene / Feature" && !hasMutType);

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

          {showMutColors && (
            <div className="pt-1">
              <MutationColorsPanel />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
