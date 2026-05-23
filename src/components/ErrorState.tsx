interface ErrorStateProps {
  error: string;
  filePath: string | null;
}

export function ErrorState({ error, filePath }: ErrorStateProps) {
  return (
    <div className="w-full bg-red-950/10 border border-red-500/20 rounded-2xl p-6 shadow-xl backdrop-blur-md animate-fade-in flex flex-col items-center justify-center text-center gap-4 py-10">
      <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>

      <div className="max-w-md">
        <h2 className="text-base font-semibold text-white tracking-tight">
          Unable to load selected file.
        </h2>
        <p className="text-xs text-zinc-400 mt-1">
          The file could not be accessed or parsed by the Local Pilot background service.
        </p>
      </div>

      {filePath && (
        <div className="w-full max-w-lg mt-2">
          <label className="text-[10px] font-semibold text-zinc-500 tracking-wider uppercase block text-left mb-1">
            Attempted File Path
          </label>
          <div className="font-mono text-xs text-red-300 bg-red-950/20 border border-red-500/10 rounded-lg px-3 py-2 text-left truncate">
            {filePath}
          </div>
        </div>
      )}

      {error && (
        <details className="w-full max-w-lg mt-1 text-left">
          <summary className="text-[11px] text-zinc-500 hover:text-zinc-400 cursor-pointer select-none outline-none">
            Technical Details
          </summary>
          <div className="font-mono text-[10px] text-zinc-500 bg-black/30 border border-white/5 rounded-lg p-3 mt-1.5 overflow-x-auto whitespace-pre-wrap">
            {error}
          </div>
        </details>
      )}

      <div className="text-[11px] text-zinc-500 mt-2">
        Please ensure the file exists and that you have appropriate read permissions.
      </div>
    </div>
  );
}
