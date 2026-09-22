import { Loader2, Inbox, AlertTriangle } from 'lucide-react'

export function LoadingSpinner({ className = 'w-8 h-8' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-12 text-slate-400">
      <Loader2 className={`${className} animate-spin text-blue-600`} />
      <span className="text-sm">Loading...</span>
    </div>
  )
}

export function EmptyState({ title = 'No data found', message = 'Add some data to see it here.' }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center animate-fade-in">
      <span className="flex items-center justify-center w-14 h-14 rounded-full bg-slate-100 text-slate-400 mb-4">
        <Inbox className="w-7 h-7" />
      </span>
      <p className="text-slate-800 font-semibold">{title}</p>
      {message && <p className="text-slate-400 text-sm mt-1 max-w-sm">{message}</p>}
    </div>
  )
}

export function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm animate-fade-in">
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

export function Card({ children, className = '' }) {
  return <div className={`card ${className}`}>{children}</div>
}

export function CardHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}