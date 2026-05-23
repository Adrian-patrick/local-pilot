export function AskSection() {
  return (
    <div className="w-full bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md animate-fade-in flex flex-col gap-4">
      <div>
        <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
          Ask Local Pilot
          <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700/50 uppercase tracking-wider">
            Coming in Stage 2
          </span>
        </h3>
        <p className="text-xs text-zinc-400">Contextual query sandbox (disabled in Prototype Stage 1)</p>
      </div>

      <div className="relative flex items-center">
        {/* Mock input field */}
        <input
          type="text"
          disabled
          placeholder="Ask anything about this file..."
          className="w-full h-12 bg-black/30 border border-white/5 rounded-xl pl-4 pr-12 text-sm text-zinc-500 placeholder-zinc-600 cursor-not-allowed"
        />

        {/* Mock submit button */}
        <button
          disabled
          className="absolute right-2 flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-800/80 text-zinc-600 cursor-not-allowed"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </div>

      <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-medium">
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Stage 1 successfully validates OS hook, argument routing, and Rust metadata parser.
      </div>
    </div>
  );
}
