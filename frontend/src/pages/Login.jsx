import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi, getErrorMessage } from '../services/api'
import { Laptop, ShieldCheck, ArrowLeftRight, BarChart3, Loader2 } from 'lucide-react'

const highlights = [
  { icon: ArrowLeftRight, label: 'Streamlined allocation workflow' },
  { icon: BarChart3, label: 'Live analytics and reports' },
  { icon: ShieldCheck, label: 'Secure admin-only access' },
]

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await authApi.login(username.trim(), password)
      login(response.data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Branding panel */}
      <div className="hidden lg:flex flex-col justify-between w-[46%] bg-navy-900 text-white p-12">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 shadow-lg shadow-blue-950/50">
            <Laptop className="w-6 h-6" />
          </span>
          <span>
            <span className="block text-lg font-bold leading-tight">Allocator</span>
            <span className="block text-xs text-blue-300/80">Asset Management</span>
          </span>
        </div>

        <div>
          <h1 className="text-3xl xl:text-4xl font-bold leading-tight tracking-tight">
            Laptop allocation,
            <br />
            made simple.
          </h1>
          <p className="mt-4 text-blue-200/80 max-w-md leading-relaxed">
            Manage laptop inventory, register interns and track every allocation — from handover to return — in one
            professional dashboard.
          </p>
          <ul className="mt-8 space-y-3">
            {highlights.map((h) => (
              <li key={h.label} className="flex items-center gap-3 text-sm text-blue-100">
                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-white/10">
                  <h.icon className="w-4 h-4 text-blue-300" />
                </span>
                {h.label}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-slate-500">© {new Date().getFullYear()} Allocator · Laptop Allocation System</p>
      </div>

      {/* Form panel */}
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-white">
              <Laptop className="w-5 h-5" />
            </span>
            <span>
              <span className="block text-base font-bold text-slate-900 leading-tight">Allocator</span>
              <span className="block text-xs text-slate-400">Asset Management</span>
            </span>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Welcome back</h2>
          <p className="text-sm text-slate-500 mt-1">Sign in to your admin account to continue</p>

          <div className="mt-8 card p-6">
            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm animate-fade-in">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="username" className="label">Username</label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                  className="input"
                  placeholder="Enter your username"
                />
              </div>
              <div>
                <label htmlFor="password" className="label">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="input"
                  placeholder="Enter your password"
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          </div>

          <p className="mt-6 text-sm text-slate-400 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-4 h-4" /> Access is restricted to authorised administrators
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login