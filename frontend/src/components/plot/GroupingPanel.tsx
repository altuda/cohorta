import { useEffect, useMemo } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useSessionStore } from "../../stores/useSessionStore";
import { useColumns } from "../../api/hooks";

function SortableValue({ id, label }: { id: string; label: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 px-2 py-1 rounded border text-xs ${
        isDragging
          ? "border-blue-400 bg-blue-50 shadow z-10"
          : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <span
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-slate-400 select-none"
        title="Drag to reorder"
      >
        ⠿
      </span>
      <span className="text-slate-700 truncate">{label}</span>
    </div>
  );
}

/** Draggable list of a grouping column's values, controlling block order. */
function SubgroupOrder({ col }: { col: string }) {
  const order = useSessionStore((s) => s.groupValueOrder[col]);
  const setGroupValueOrder = useSessionStore((s) => s.setGroupValueOrder);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (!order || order.length < 2) return null;

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id || !order) return;
    const oldIndex = order.indexOf(active.id as string);
    const newIndex = order.indexOf(over.id as string);
    setGroupValueOrder(col, arrayMove(order, oldIndex, newIndex));
  }

  return (
    <div className="mt-1.5 ml-1 pl-2 border-l-2 border-slate-100">
      <p className="text-[10px] text-slate-400 mb-1">Drag to reorder groups</p>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <div className="space-y-1">
            {order.map((v) => (
              <SortableValue key={v} id={v} label={v} />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}

export default function GroupingPanel() {
  const columns = useSessionStore((s) => s.columns);
  const roles = useSessionStore((s) => s.roles);
  const sessionId = useSessionStore((s) => s.sessionId);
  const groupColumns = useSessionStore((s) => s.groupColumns);
  const setGroupColumns = useSessionStore((s) => s.setGroupColumns);
  const groupValueOrder = useSessionStore((s) => s.groupValueOrder);
  const setGroupValueOrder = useSessionStore((s) => s.setGroupValueOrder);

  const { data: colData } = useColumns(sessionId);

  // Map of column -> its distinct values (only for columns with <=50 unique).
  const uniqueMap = useMemo(() => {
    const m: Record<string, string[]> = {};
    (colData?.columns ?? []).forEach((c) => {
      if (c.unique_values) m[c.name] = c.unique_values;
    });
    return m;
  }, [colData]);

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

  // Seed a default block order (the column's distinct values) the first time a
  // grouping column is chosen, so the draggable list matches the plot.
  useEffect(() => {
    groupColumns.filter(Boolean).forEach((gc) => {
      if (!groupValueOrder[gc] && uniqueMap[gc]?.length) {
        setGroupValueOrder(gc, uniqueMap[gc]);
      }
    });
  }, [groupColumns, uniqueMap, groupValueOrder, setGroupValueOrder]);

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
          <div key={i}>
            <label className="block">
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
            {gc && uniqueMap[gc] && <SubgroupOrder col={gc} />}
            {gc && colData && !uniqueMap[gc] && (
              <p className="text-[10px] text-slate-400 mt-1 ml-1">
                Too many distinct values to reorder
              </p>
            )}
          </div>
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
