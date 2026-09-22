import { useEffect } from 'react'
import { X } from 'lucide-react'

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Modal({ open, onClose, title, icon, iconClass = 'bg-blue-50 text-blue-600', children, footer, maxWidth = 'max-w-lg' }) {
  useEffect(() => {
    if (!open) return undefined
    const handler = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-[2px] animate-fade-in" onClick={onClose} />
      <div className={`relative w-full ${maxWidth} max-h-[90vh] overflow-hidden rounded-2xl bg-white shadow-popover flex flex-col animate-fade-up`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            {icon && (
              <span className={`flex items-center justify-center w-9 h-9 rounded-lg ${iconClass}`}>
                {icon}
              </span>
            )}
            <h3 className="text-base font-semibold text-slate-900">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export function BatchBadge({ batch }) {
  const styles =
    batch === 'Morning'
      ? 'bg-blue-50 text-blue-700 ring-blue-200'
      : batch === 'Afternoon'
        ? 'bg-indigo-50 text-indigo-700 ring-indigo-200'
        : 'bg-violet-50 text-violet-700 ring-violet-200'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full ring-1 ${styles}`}>
      {batch}
    </span>
  )
}

export function StatCard({ icon, label, value, hint, iconClass = 'bg-blue-50 text-blue-600', trend }) {
  return (
    <div className="card p-5 flex flex-col hover:shadow-card-hover transition-shadow">
      <div className="flex items-start justify-between">
        <div className={`flex items-center justify-center w-11 h-11 rounded-xl ${iconClass}`}>
          {icon}
        </div>
        {trend && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-semibold">
            {trend}
          </span>
        )}
      </div>
      <p className="mt-4 text-3xl font-bold text-slate-900 tracking-tight">{value}</p>
      <p className="mt-1 text-sm font-medium text-slate-600">{label}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  )
}

export function SectionCard({ title, subtitle, actions, children, className = '', bodyClassName = '' }) {
  return (
    <div className={`card ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </div>
  )
}