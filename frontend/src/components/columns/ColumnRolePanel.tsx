import { useEffect } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { useSetRoles } from "../../api/hooks";
import ColumnRoleCard from "./ColumnRoleCard";

export default function ColumnRolePanel() {
  const columns = useSessionStore((s) => s.columns);
  const roles = useSessionStore((s) => s.roles);
  const setMutationTypes = useSessionStore((s) => s.setMutationTypes);
  const setAnnotationUniqueValues = useSessionStore(
    (s) => s.setAnnotationUniqueValues
  );
  const setRolesMut = useSetRoles();

  // Sync roles with backend to get mutation types + annotation unique values
  useEffect(() => {
    const hasSample = Object.values(roles).includes("Sample ID");
    if (!hasSample) return;
    setRolesMut.mutate(roles, {
      onSuccess: (data) => {
        if (data.mutation_types) setMutationTypes(data.mutation_types);
        if (data.annotation_unique_values) {
          setAnnotationUniqueValues(data.annotation_unique_values);
        }
      },
      onError: (err) => {
        console.error("Failed to sync roles:", err);
      },
    });
  }, [roles]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
        Column Configuration
      </h2>
      <div className="space-y-1.5">
        {columns.map((col) => (
          <ColumnRoleCard key={col} col={col} />
        ))}
      </div>
    </div>
  );
}
