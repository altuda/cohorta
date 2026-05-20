import { useSessionStore } from "../../stores/useSessionStore";
import { usePaletteColors } from "../../api/hooks";
import ColumnRolePanel from "../columns/ColumnRolePanel";
import TrackOrderPanel from "../columns/TrackOrderPanel";
import PlotSettingsPanel from "../plot/PlotSettingsPanel";
import GroupingPanel from "../plot/GroupingPanel";
import MutationColorsPanel from "../plot/MutationColorsPanel";

export default function Sidebar() {
  const sessionId = useSessionStore((s) => s.sessionId);

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
      <div className="p-4 space-y-6">
        <ColumnRolePanel />
        <hr className="border-slate-200" />
        <TrackOrderPanel />
        <hr className="border-slate-200" />
        <PlotSettingsPanel />
        <hr className="border-slate-200" />
        <GroupingPanel />
        <hr className="border-slate-200" />
        <MutationColorsPanel />
      </div>
    </aside>
  );
}
