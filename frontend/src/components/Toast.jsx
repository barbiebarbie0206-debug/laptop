import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const toastStyles = {
  success: {
    wrap: 'bg-white border-l-4 border-emerald-500 shadow-popover',
    icon: <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />,
  },
  error: {
    wrap: 'bg-white border-l-4 border-red-500 shadow-popover',
    icon: <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />,
  },
  info: {
    wrap: 'bg-white border-l-4 border-blue-500 shadow-popover',
    icon: <Info className="w-5 h-5 text-blue-500 shrink-0" />,
  },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => dismiss(id), 4000)
  }, [dismiss])

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className="fixed top-4 right-4 z-[100] space-y-3 w-80 max-w-[90vw]">
        {toasts.map((t) => {
          const style = toastStyles[t.type] || toastStyles.info
          return (
            <div key={t.id} className={`flex items-start gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-700 animate-slide-in ${style.wrap}`}>
              {style.icon}
              <span className="flex-1">{t.message}</span>
              <button
                onClick={() => dismiss(t.id)}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}