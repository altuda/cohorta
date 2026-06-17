import { useState } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { usePaletteColors } from "../../api/hooks";
import AccordionSection from "./AccordionSection";
import ColumnRolePanel from "../columns/ColumnRolePanel";
import TrackOrderPanel from "../columns/TrackOrderPanel";
import PlotSettingsPanel from "../plot/PlotSettingsPanel";
import GroupingPanel from "../plot/GroupingPanel";

export default function Sidebar() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const annotationOrder = useSessionStore((s) => s.annotationOrder);

  // Single-open accordion; Columns is expanded by default.
  const [open, setOpen] = useState("columns");
  const toggle = (id: string) => setOpen((cur) => (cur === id ? "" : id));

  // Compute sidebar width from palette size:
  // ml-8 (32px) + n swatches * (20px + 4px gap) + padding (32px)
  const { data: paletteColors } = usePaletteColors("tab10", 10);
  const nColors = paletteColors?.colors?.length ?? 10;
  const minWidth = 32 + nColors * 24 + 32;
  const sidebarWidth = Math.max(320, minWidth);

  if (!sessionId) return null;

  return (
    <aside
      className="shrink-0 border-r border-slate-200 bg-white overflow-y-auto h-screen sticky top-0"
      style={{ width: sidebarWidth }}
    >
      <div className="p-4 space-y-2">
        <AccordionSection
          title="Columns & roles"
          isOpen={open === "columns"}
          onToggle={() => toggle("columns")}
        >
          <ColumnRolePanel />
        </AccordionSection>

        {annotationOrder.length >= 2 && (
          <AccordionSection
            title="Track order"
            isOpen={open === "order"}
            onToggle={() => toggle("order")}
          >
            <TrackOrderPanel />
          </AccordionSection>
        )}

        <AccordionSection
          title="Plot settings"
          isOpen={open === "plot"}
          onToggle={() => toggle("plot")}
        >
          <PlotSettingsPanel />
        </AccordionSection>

        <AccordionSection
          title="Grouping"
          isOpen={open === "grouping"}
          onToggle={() => toggle("grouping")}
        >
          <GroupingPanel />
        </AccordionSection>
      </div>
    </aside>
  );
}
