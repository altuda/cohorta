import { useCallback, useEffect, useRef, useState } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { useRender } from "../../api/hooks";
import { clearSessionId } from "../../api/client";
import Sidebar from "./Sidebar";
import FileUploader from "../upload/FileUploader";
import DataPreview from "../upload/DataPreview";
import PlotPreview from "../preview/PlotPreview";
import DownloadBar from "../preview/DownloadBar";

export default function AppShell() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const buildRenderRequest = useSessionStore((s) => s.buildRenderRequest);
  const setRenderResult = useSessionStore((s) => s.setRenderResult);
  const reset = useSessionStore((s) => s.reset);
  const render = useRender();

  const [autoRender, setAutoRender] = useState(true);
  const [warnings, setWarnings] = useState<string[]>([]);

  // Keep a stable ref to the render mutation so the auto-render effect
  // doesn't re-fire every time the mutation object changes identity.
  const renderRef = useRef(render);
  renderRef.current = render;
  const buildRef = useRef(buildRenderRequest);
  buildRef.current = buildRenderRequest;

  const handleGenerate = useCallback(() => {
    const req = buildRef.current();
    renderRef.current.mutate(req, {
      onSuccess: (data) => {
        setRenderResult(data.png_url, data.pdf_url, data.csv_url);
        setWarnings(data.warnings ?? []);
      },
    });
  }, [setRenderResult]);

  // Build a snapshot of all render-relevant state for change detection
  const roles = useSessionStore((s) => s.roles);
  const displayNames = useSessionStore((s) => s.displayNames);
  const annotationOrder = useSessionStore((s) => s.annotationOrder);
  const annotationTypes = useSessionStore((s) => s.annotationTypes);
  const annotationColors = useSessionStore((s) => s.annotationColors);
  const trackOptions = useSessionStore((s) => s.trackOptions);
  const dataRowCmaps = useSessionStore((s) => s.dataRowCmaps);
  const mutationColors = useSessionStore((s) => s.mutationColors);
  const groupColumns = useSessionStore((s) => s.groupColumns);
  const groupValueOrder = useSessionStore((s) => s.groupValueOrder);
  const topNGenes = useSessionStore((s) => s.topNGenes);
  const showTmb = useSessionStore((s) => s.showTmb);
  const showGeneFreq = useSessionStore((s) => s.showGeneFreq);
  const showSampleLabels = useSessionStore((s) => s.showSampleLabels);
  const annotationsPosition = useSessionStore((s) => s.annotationsPosition);
  const title = useSessionStore((s) => s.title);
  const figWidth = useSessionStore((s) => s.figWidth);
  const fontsize = useSessionStore((s) => s.fontsize);

  const configFingerprint = JSON.stringify({
    roles, displayNames, annotationOrder, annotationTypes,
    annotationColors, trackOptions, dataRowCmaps, mutationColors,
    groupColumns, groupValueOrder, topNGenes, showTmb, showGeneFreq,
    showSampleLabels, annotationsPosition, title, figWidth, fontsize,
  });

  // Debounced auto-render
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const prevFingerprintRef = useRef<string>("");
  const hasRenderedOnce = useRef(false);

  useEffect(() => {
    if (!autoRender || !sessionId) return;
    if (prevFingerprintRef.current === configFingerprint) return;
    prevFingerprintRef.current = configFingerprint;
    if (!hasRenderedOnce.current) {
      hasRenderedOnce.current = true;
      return;
    }

    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(handleGenerate, 800);
    return () => clearTimeout(timerRef.current);
  }, [configFingerprint, autoRender, sessionId, handleGenerate]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 min-w-0 max-w-7xl mx-auto">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              Oncoplot Builder
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Upload a mutation dataset, configure columns, and generate a
              publication-quality oncoplot.
            </p>
          </div>
          {sessionId && (
            <button
              onClick={() => { clearSessionId(); reset(); }}
              className="text-xs text-slate-400 hover:text-slate-600 px-3 py-1 border border-slate-200 rounded-lg"
            >
              New session
            </button>
          )}
        </header>

        {!sessionId ? (
          <FileUploader />
        ) : (
          <>
            <DataPreview />

            <div className="flex items-center gap-3 mt-4">
              <button
                onClick={handleGenerate}
                disabled={render.isPending}
                className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {render.isPending ? "Generating..." : "Generate Oncoplot"}
              </button>
              <label className="flex items-center gap-2 text-sm text-slate-600 shrink-0">
                <input
                  type="checkbox"
                  checked={autoRender}
                  onChange={(e) => setAutoRender(e.target.checked)}
                />
                Auto
              </label>
            </div>

            {render.isError && (
              <div className="mt-3 p-3 rounded-lg bg-red-50 border border-red-200">
                <p className="text-sm text-red-700 font-medium">Render failed</p>
                <p className="text-xs text-red-600 mt-1">
                  {(render.error as Error).message}
                </p>
              </div>
            )}

            {warnings.length > 0 && (
              <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200">
                {warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-700">{w}</p>
                ))}
              </div>
            )}

            <div className="mt-6">
              <PlotPreview isRendering={render.isPending} />
              <DownloadBar />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
