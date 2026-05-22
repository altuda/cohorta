import { useSessionStore } from "../../stores/useSessionStore";

export default function PlotSettingsPanel() {
  const s = useSessionStore();
  const hasGene = Object.values(s.roles).includes("Gene / Feature");

  return (
    <div>
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
        Plot Settings
      </h2>
      <div className="space-y-2">
        {hasGene && (
          <label className="block">
            <span className="text-xs text-slate-500">Top N genes</span>
            <input
              type="range"
              min={5}
              max={50}
              value={s.topNGenes}
              onChange={(e) =>
                s.setPlotSetting("topNGenes", Number(e.target.value))
              }
              className="w-full mt-0.5"
            />
            <span className="text-xs text-slate-600">{s.topNGenes}</span>
          </label>
        )}

        {hasGene && (
          <>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={s.showTmb}
                onChange={(e) =>
                  s.setPlotSetting("showTmb", e.target.checked)
                }
              />
              <span className="text-slate-700">TMB bar</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={s.showGeneFreq}
                onChange={(e) =>
                  s.setPlotSetting("showGeneFreq", e.target.checked)
                }
              />
              <span className="text-slate-700">Gene frequency bar</span>
            </label>
          </>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={s.showSampleLabels}
            onChange={(e) =>
              s.setPlotSetting("showSampleLabels", e.target.checked)
            }
          />
          <span className="text-slate-700">Sample labels</span>
        </label>

        {/* In oncoplot mode this controls annotation-track placement (always
            relevant); in annotation-only mode it only positions the sample
            labels, so hide it unless labels are shown. */}
        {(hasGene || s.showSampleLabels) && (
          <label className="block">
            <span className="text-xs text-slate-500">
              {hasGene ? "Annotation position" : "Sample labels position"}
            </span>
            <div className="flex gap-3 mt-0.5">
              {["bottom", "top"].map((pos) => (
                <label key={pos} className="flex items-center gap-1 text-sm">
                  <input
                    type="radio"
                    name="annotPos"
                    value={pos}
                    checked={s.annotationsPosition === pos}
                    onChange={() =>
                      s.setPlotSetting("annotationsPosition", pos)
                    }
                  />
                  <span className="capitalize text-slate-700">{pos}</span>
                </label>
              ))}
            </div>
          </label>
        )}

        <label className="block">
          <span className="text-xs text-slate-500">Title</span>
          <input
            type="text"
            value={s.title ?? ""}
            onChange={(e) =>
              s.setPlotSetting("title", e.target.value || null)
            }
            placeholder="No title"
            className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
          />
        </label>

        <label className="block">
          <span className="text-xs text-slate-500">
            Figure width: {s.figWidth}in
          </span>
          <input
            type="range"
            min={8}
            max={30}
            value={s.figWidth}
            onChange={(e) =>
              s.setPlotSetting("figWidth", Number(e.target.value))
            }
            className="w-full mt-0.5"
          />
        </label>

        <label className="block">
          <span className="text-xs text-slate-500">
            Font size: {s.fontsize}
          </span>
          <input
            type="range"
            min={5}
            max={14}
            value={s.fontsize}
            onChange={(e) =>
              s.setPlotSetting("fontsize", Number(e.target.value))
            }
            className="w-full mt-0.5"
          />
        </label>
      </div>
    </div>
  );
}
