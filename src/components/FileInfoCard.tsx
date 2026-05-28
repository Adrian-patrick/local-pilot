import { FileMetadata } from "../types/file";

interface FileInfoCardProps {
  metadata: FileMetadata;
}

export function FileInfoCard({ metadata }: FileInfoCardProps) {
  // Helper to format bytes to human readable form
  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  // Helper to get extension badge color based on file type
  const getTypeColor = (ext: string) => {
    if (ext === "FOLDER") return "bg-yellow-500/10 text-yellow-300 border-yellow-500/20";
    
    const blueTypes = ["PDF", "DOC", "DOCX"];
    const greenTypes = ["XLS", "XLSX", "CSV"];
    const purpleTypes = ["PNG", "JPG", "JPEG", "SVG", "GIF"];
    const orangeTypes = ["PY", "JS", "TS", "TSX", "JSX", "HTML", "CSS", "JSON", "RS", "GO", "CPP", "C", "CS", "SH"];

    if (blueTypes.includes(ext)) return "bg-blue-500/10 text-blue-300 border-blue-500/20";
    if (greenTypes.includes(ext)) return "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
    if (purpleTypes.includes(ext)) return "bg-purple-500/10 text-purple-300 border-purple-500/20";
    if (orangeTypes.includes(ext)) return "bg-amber-500/10 text-amber-300 border-amber-500/20";
    return "bg-zinc-500/10 text-zinc-300 border-zinc-500/20";
  };

  return (
    <div className="w-full bg-white/[0.03] border border-white/5 rounded-2xl p-6 shadow-xl backdrop-blur-md animate-fade-in flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`flex items-center justify-center w-11 h-11 rounded-xl border ${metadata.is_dir ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-400" : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"}`}>
            {metadata.is_dir ? (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
          </div>
          <div>
            <span className={`text-[11px] font-semibold tracking-wider uppercase block mb-0.5 ${metadata.is_dir ? "text-yellow-400" : "text-indigo-400"}`}>
              {metadata.is_dir ? "Active Directory" : "Active Context"}
            </span>
            <h2 className="text-base font-semibold text-white tracking-tight leading-none truncate max-w-[400px]">
              {metadata.file_name}
            </h2>
          </div>
        </div>

        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${getTypeColor(metadata.extension)}`}>
          {metadata.extension || "FILE"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-white/5">
        <div className="md:col-span-2">
          <label className="text-[10px] font-semibold text-zinc-500 tracking-wider uppercase block mb-1">
            {metadata.is_dir ? "Full Directory Path" : "Full File Path"}
          </label>
          <div className="font-mono text-xs text-zinc-300 bg-black/20 border border-white/5 rounded-lg px-3 py-2 select-all truncate">
            {metadata.full_path}
          </div>
        </div>

        <div>
          <label className="text-[10px] font-semibold text-zinc-500 tracking-wider uppercase block mb-1">
            {metadata.is_dir ? "Type" : "File Size"}
          </label>
          <span className="text-sm font-medium text-white">
            {metadata.is_dir ? "Directory Folder" : formatSize(metadata.file_size)}
          </span>
        </div>

        <div>
          <label className="text-[10px] font-semibold text-zinc-500 tracking-wider uppercase block mb-1">
            Last Modified
          </label>
          <span className="text-sm font-medium text-white">
            {metadata.last_modified}
          </span>
        </div>
      </div>
    </div>
  );
}
