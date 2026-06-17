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

function SortableItem({ id, label }: { id: string; label: string }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
        isDragging
          ? "border-blue-400 bg-blue-50 shadow-md z-10"
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

export default function TrackOrderPanel() {
  const annotationOrder = useSessionStore((s) => s.annotationOrder);
  const displayNames = useSessionStore((s) => s.displayNames);
  const setAnnotationOrder = useSessionStore((s) => s.setAnnotationOrder);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  if (annotationOrder.length < 2) return null;

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = annotationOrder.indexOf(active.id as string);
    const newIndex = annotationOrder.indexOf(over.id as string);
    setAnnotationOrder(arrayMove(annotationOrder, oldIndex, newIndex));
  }

  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">
        Drag to reorder annotation tracks
      </p>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={annotationOrder}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-1">
            {annotationOrder.map((col) => (
              <SortableItem
                key={col}
                id={col}
                label={displayNames[col] ?? col}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
