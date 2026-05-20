import { useSessionStore } from "../../stores/useSessionStore";
import ColumnRolePanel from "../columns/ColumnRolePanel";
import TrackOrderPanel from "../columns/TrackOrderPanel";
import PlotSettingsPanel from "../plot/PlotSettingsPanel";
import GroupingPanel from "../plot/GroupingPanel";
import MutationColorsPanel from "../plot/MutationColorsPanel";

export default function Sidebar() {
  const sessionId = useSessionStore((s) => s.sessionId);

  if (!sessionId) return null;

  return (
    <aside className="w-80 shrink-0 border-r border-slate-200 bg-white overflow-y-auto h-screen sticky top-0">
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
