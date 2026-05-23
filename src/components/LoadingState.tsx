export function LoadingState() {
  return (
    <div className="w-full bg-white/[0.03] border border-white/5 rounded-2xl p-6 shadow-xl backdrop-blur-md animate-pulse flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-white/5" />
          <div className="flex flex-col gap-1.5">
            <div className="w-20 h-3 bg-white/5 rounded" />
            <div className="w-40 h-4 bg-white/10 rounded" />
          </div>
        </div>
        <div className="w-14 h-5 bg-white/5 rounded-full" />
      </div>

      <div className="flex flex-col gap-4 pt-3 border-t border-white/5">
        <div>
          <div className="w-24 h-2.5 bg-white/5 rounded mb-1.5" />
          <div className="w-full h-8 bg-white/5 rounded-lg" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="w-16 h-2.5 bg-white/5 rounded mb-1.5" />
            <div className="w-20 h-4 bg-white/10 rounded" />
          </div>
          <div>
            <div className="w-20 h-2.5 bg-white/5 rounded mb-1.5" />
            <div className="w-28 h-4 bg-white/10 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}
