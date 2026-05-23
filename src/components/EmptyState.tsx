export function EmptyState() {
  return (
    <div className="w-full bg-white/[0.03] border border-white/5 rounded-2xl p-8 shadow-xl backdrop-blur-md animate-fade-in flex flex-col items-center justify-center text-center gap-5 py-12">
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
        {/* Navigation/Target icon */}
        <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
        </svg>
      </div>

      <div className="max-w-md">
        <h2 className="text-base font-semibold text-white tracking-tight">
          Ready for File Context
        </h2>
        <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed">
          Local Pilot runs as an OS-native contextual workspace. To load a file, simply right-click any file in your Explorer and choose <strong className="text-indigo-400">"Ask Local Pilot"</strong>.
        </p>
      </div>

      {/* Modern interactive step-by-step visual */}
      <div className="w-full max-w-sm bg-black/20 border border-white/5 rounded-xl p-4 text-left flex flex-col gap-3.5 mt-2">
        <span className="text-[10px] font-semibold text-indigo-400 tracking-wider uppercase block">
          How to use in Stage 1
        </span>

        <div className="flex items-start gap-3">
          <div className="flex items-center justify-center w-5 h-5 rounded-full bg-zinc-800 text-[10px] text-zinc-400 font-semibold border border-zinc-700/50 shrink-0 mt-0.5">
            1
          </div>
          <p className="text-xs text-zinc-300">
            Open <strong className="text-white">Windows Explorer</strong>.
          </p>
        </div>

        <div className="flex items-start gap-3">
          <div className="flex items-center justify-center w-5 h-5 rounded-full bg-zinc-800 text-[10px] text-zinc-400 font-semibold border border-zinc-700/50 shrink-0 mt-0.5">
            2
          </div>
          <p className="text-xs text-zinc-300">
            Right-click any file and select <strong className="text-white">"Ask Local Pilot"</strong> from the context menu.
          </p>
        </div>

        <div className="flex items-start gap-3">
          <div className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-500/20 text-[10px] text-indigo-400 font-semibold border border-indigo-500/30 shrink-0 mt-0.5">
            3
          </div>
          <p className="text-xs text-zinc-300">
            The Local Pilot desktop app opens with the selected file's metadata parsed and displayed instantly.
          </p>
        </div>
      </div>
      
      <div className="text-[10px] text-indigo-400/60 font-semibold border border-indigo-400/10 rounded-full px-3 py-1 bg-indigo-500/[0.02]">
        Windows Context Menu is integrated and fully functional!
      </div>
    </div>
  );
}
