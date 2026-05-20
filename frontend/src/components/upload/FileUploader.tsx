import { useCallback } from "react";
import { useUploadFile } from "../../api/hooks";
import { useSessionStore } from "../../stores/useSessionStore";

export default function FileUploader() {
  const upload = useUploadFile();
  const setUploadResult = useSessionStore((s) => s.setUploadResult);

  const handleFile = useCallback(
    (file: File) => {
      upload.mutate(file, {
        onSuccess: (data) => setUploadResult(data),
      });
    },
    [upload, setUploadResult]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="w-full max-w-lg border-2 border-dashed border-slate-300 rounded-xl p-12 text-center hover:border-blue-400 hover:bg-blue-50/50 transition-colors cursor-pointer"
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <div className="text-4xl mb-3">📂</div>
        <p className="text-lg font-medium text-slate-700">
          Drop your <code>.xlsx</code> file here
        </p>
        <p className="text-sm text-slate-400 mt-1">or click to browse</p>
        <input
          id="file-input"
          type="file"
          accept=".xlsx"
          onChange={handleChange}
          className="hidden"
        />
      </div>

      {upload.isPending && (
        <p className="mt-4 text-blue-600 animate-pulse">Uploading…</p>
      )}
      {upload.isError && (
        <p className="mt-4 text-red-600">
          Upload failed: {upload.error.message}
        </p>
      )}
    </div>
  );
}
