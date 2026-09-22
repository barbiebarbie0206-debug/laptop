const statusStyles = {
  ACTIVE: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  RETURNED: 'bg-blue-50 text-blue-700 ring-blue-200',
  CANCELLED: 'bg-slate-100 text-slate-600 ring-slate-200',
  COMPLETED: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  FREE: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  ALLOCATED: 'bg-blue-50 text-blue-700 ring-blue-200',
  MAINTENANCE: 'bg-amber-50 text-amber-700 ring-amber-200',
  INACTIVE: 'bg-slate-100 text-slate-500 ring-slate-200',
}

const dotColors = {
  ACTIVE: 'bg-emerald-500',
  RETURNED: 'bg-blue-500',
  CANCELLED: 'bg-slate-400',
  COMPLETED: 'bg-indigo-500',
  FREE: 'bg-emerald-500',
  ALLOCATED: 'bg-blue-500',
  MAINTENANCE: 'bg-amber-500',
  INACTIVE: 'bg-slate-400',
}

const labelOverrides = {
  MAINTENANCE: 'Unavailable',
}

export default function StatusBadge({ status, className = '' }) {
  const key = String(status || '').toUpperCase()
  const display = labelOverrides[key] || status
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ring-1 ${
        statusStyles[key] || 'bg-slate-100 text-slate-600 ring-slate-200'
      } ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColors[key] || 'bg-slate-400'}`} />
      {display}
    </span>
  )
}