export function Header() {
  return (
    <header className="flex items-center justify-between pb-6 border-b border-white/5 animate-fade-in">
      <div className="flex items-center gap-3">
        {/* Custom premium logo icon */}
        <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-lg shadow-indigo-500/20">
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
          {/* Subtle glow dot */}
          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 border border-slate-900 shadow-sm" />
        </div>
        
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
            Local Pilot
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 uppercase tracking-widest">
              Stage 1
            </span>
          </h1>
          <p className="text-xs text-zinc-400">Contextual workspace agent</p>
        </div>
      </div>

      <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/5 border border-white/5 text-[11px] text-zinc-400 font-medium">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Connected
      </div>
    </header>
  );
}
