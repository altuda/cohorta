import { useSessionStore } from "../../stores/useSessionStore";

export default function PlotPreview({ isRendering }: { isRendering?: boolean }) {
  const pngUrl = useSessionStore((s) => s.pngUrl);
  const renderVersion = useSessionStore((s) => s.renderVersion);

  if (!pngUrl && !isRendering) return null;

  return (
    <div className="relative border border-slate-200 rounded-xl overflow-hidden bg-white">
      {pngUrl && (
        <img
          src={`${pngUrl}?v=${renderVersion}`}
          alt="Oncoplot"
          className={`w-full transition-opacity ${isRendering ? "opacity-40" : "opacity-100"}`}
        />
      )}
      {isRendering && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-slate-500 font-medium">
              Rendering...
            </span>
          </div>
        </div>
      )}
      {!pngUrl && isRendering && (
        <div className="h-64" />
      )}
    </div>
  );
}
