import { useSessionStore } from "../../stores/useSessionStore";

function downloadUrl(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}

export default function DownloadBar() {
  const { pngUrl, pdfUrl, csvUrl } = useSessionStore();

  if (!pngUrl) return null;

  return (
    <div className="flex gap-3 mt-4">
      <button
        onClick={() => downloadUrl(pngUrl, "oncoplot.png")}
        className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        Download PNG
      </button>
      {pdfUrl && (
        <button
          onClick={() => downloadUrl(pdfUrl, "oncoplot.pdf")}
          className="px-4 py-2 rounded-lg bg-slate-600 text-white text-sm font-medium hover:bg-slate-700 transition-colors"
        >
          Download PDF
        </button>
      )}
      {csvUrl && (
        <button
          onClick={() => downloadUrl(csvUrl, "mutation_matrix.csv")}
          className="px-4 py-2 rounded-lg bg-slate-600 text-white text-sm font-medium hover:bg-slate-700 transition-colors"
        >
          Download CSV
        </button>
      )}
    </div>
  );
}
