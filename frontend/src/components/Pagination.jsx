import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page, totalPages, total, pageSize, onPageChange, onPageSizeChange }) {
  if (totalPages <= 1 && total === 0) return null
  const pages = []
  const start = Math.max(1, page - 2)
  const end = Math.min(totalPages, page + 2)
  for (let i = start; i <= end; i++) pages.push(i)

  const pageBtn = (p, active) =>
    `flex items-center justify-center min-w-[32px] h-8 px-2 text-sm font-medium rounded-lg border transition-colors ${
      active
        ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700'
        : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
    }`

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-5 py-3.5 border-t border-slate-200">
      <p className="text-sm text-slate-500">
        Showing{' '}
        <span className="font-medium text-slate-700">{total === 0 ? 0 : (page - 1) * pageSize + 1}</span>–
        <span className="font-medium text-slate-700">{Math.min(page * pageSize, total)}</span> of{' '}
        <span className="font-medium text-slate-700">{total}</span>
      </p>
      <div className="flex items-center gap-2">
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="px-2 py-1.5 text-xs border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {[5, 10, 25, 50].map((s) => (
            <option key={s} value={s}>{s} / page</option>
          ))}
        </select>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center justify-center w-8 h-8 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Previous page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          {start > 1 && (
            <>
              <button onClick={() => onPageChange(1)} className={pageBtn(1, false)}>1</button>
              {start > 2 && <span className="px-1 text-slate-400">…</span>}
            </>
          )}
          {pages.map((p) => (
            <button key={p} onClick={() => onPageChange(p)} className={pageBtn(p, p === page)}>
              {p}
            </button>
          ))}
          {end < totalPages && (
            <>
              {end < totalPages - 1 && <span className="px-1 text-slate-400">…</span>}
              <button onClick={() => onPageChange(totalPages)} className={pageBtn(totalPages, false)}>{totalPages}</button>
            </>
          )}
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center justify-center w-8 h-8 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Next page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}