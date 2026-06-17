import { useEffect, useState, useRef, useMemo } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { usePalettes, usePaletteColors } from "../../api/hooks";
import { HexColorPicker } from "react-colorful";

function MutTypeColorPicker({
  mt,
  defaultColor,
  palColors,
}: {
  mt: string;
  defaultColor: string;
  palColors: string[];
}) {
  const color = useSessionStore((s) => s.mutationColors[mt] ?? defaultColor);
  const setMutationColor = useSessionStore((s) => s.setMutationColor);
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const handleOpen = () => {
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const popH = 220;
      setPos({
        top: spaceBelow < popH ? rect.top - popH - 4 : rect.bottom + 4,
        left: rect.left,
      });
    }
    setOpen(!open);
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <div className="relative inline-block">
          <button
            ref={btnRef}
            onClick={handleOpen}
            className="w-6 h-6 rounded border border-slate-300 shrink-0"
            style={{ backgroundColor: color }}
          />
          {open && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
              <div
                className="fixed z-50 bg-white rounded-lg shadow-lg border p-2"
                style={{ top: pos.top, left: pos.left }}
              >
                <HexColorPicker
                  color={color}
                  onChange={(c) => setMutationColor(mt, c)}
                  style={{ width: 160, height: 120 }}
                />
                <input
                  type="text"
                  value={color}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (/^#[0-9a-fA-F]{0,6}$/.test(v)) setMutationColor(mt, v);
                  }}
                  className="mt-1 w-full text-xs font-mono px-2 py-1 border border-slate-200 rounded text-center"
                  spellCheck={false}
                />
              </div>
            </>
          )}
        </div>
        <span className="text-xs text-slate-700 truncate flex-1">{mt}</span>
      </div>
      <div className="flex flex-wrap gap-1 pl-0.5 pt-0.5">
        {palColors.map((pc) => (
          <button
            key={pc}
            onClick={() => setMutationColor(mt, pc)}
            className={`w-5 h-5 rounded-sm border-2 transition-transform ${
              color === pc
                ? "border-slate-800 scale-110"
                : "border-transparent hover:border-slate-400"
            }`}
            style={{ backgroundColor: pc }}
            title={pc}
          />
        ))}
      </div>
    </div>
  );
}

export default function MutationColorsPanel() {
  const roles = useSessionStore((s) => s.roles);
  const mutationTypes = useSessionStore((s) => s.mutationTypes);
  const mutationColors = useSessionStore((s) => s.mutationColors);
  const setMutationColorsBatch = useSessionStore((s) => s.setMutationColorsBatch);

  const hasGene = Object.values(roles).includes("Gene / Feature");
  const { data: palettes } = usePalettes();

  const [palette, setPalette] = useState("tab10");
  const [singleMode, setSingleMode] = useState(false);
  const [singleColor, setSingleColor] = useState("#1f77b4");

  const n = Math.max(mutationTypes.length, 1);
  // `paletteColors` (n, spread evenly) drives the auto-assigned defaults, while
  // the quick-pick swatch row shows the fuller palette so the colours offered
  // aren't capped to the number of groups.
  const { data: paletteColors } = usePaletteColors(palette, n);
  const { data: pickerPalette } = usePaletteColors(palette, Math.max(n, 10));
  const dedupedPalColors = useMemo(
    () => [...new Set(pickerPalette?.colors ?? [])],
    [pickerPalette],
  );

  // Apply single color or palette defaults — single batch update
  useEffect(() => {
    if (!paletteColors?.colors || !mutationTypes.length) return;
    const defaults = paletteColors.colors;
    const batch: Record<string, string> = {};
    let changed = false;
    for (let i = 0; i < mutationTypes.length; i++) {
      const mt = mutationTypes[i];
      if (singleMode) {
        batch[mt] = singleColor;
        changed = true;
      } else if (!mutationColors[mt]) {
        batch[mt] = defaults[i % defaults.length];
        changed = true;
      }
    }
    if (changed) setMutationColorsBatch(batch);
  }, [mutationTypes, paletteColors, singleMode, singleColor]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hasGene) return null;

  const shown = mutationTypes.slice(0, 20);

  return (
    <div>
      <div className="space-y-2">
        <label className="block">
          <span className="text-xs text-slate-500">Palette</span>
          <select
            value={palette}
            onChange={(e) => setPalette(e.target.value)}
            className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
          >
            {(palettes?.categorical ?? []).map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={singleMode}
            onChange={(e) => setSingleMode(e.target.checked)}
          />
          <span className="text-slate-700">Use single colour</span>
        </label>

        {singleMode ? (
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={singleColor}
              onChange={(e) => setSingleColor(e.target.value)}
              className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
            />
            <span className="text-xs text-slate-500">{singleColor}</span>
          </div>
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {shown.map((mt) => (
              <MutTypeColorPicker
                key={mt}
                mt={mt}
                defaultColor={
                  paletteColors?.colors[
                    mutationTypes.indexOf(mt) %
                      (paletteColors?.colors.length || 1)
                  ] ?? "#808080"
                }
                palColors={dedupedPalColors}
              />
            ))}
            {mutationTypes.length > 20 && (
              <p className="text-xs text-slate-400">
                Showing 20 of {mutationTypes.length}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
