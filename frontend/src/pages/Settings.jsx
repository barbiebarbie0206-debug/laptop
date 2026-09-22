import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Settings as SettingsIcon, ShieldCheck, UserCircle, KeyRound, LogOut, Database, Clock, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../services/api'
import { PageHeader } from '../components/ui'
import { Card, ErrorBanner } from '../components/StateComponents'

function initials(name) {
  const parts = String(name || 'U').split(' ').filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || 'U'
}

function Settings() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await authApi.me()
        if (!cancelled) setProfile(res.data)
      } catch (err) {
        if (!cancelled) setError(String(err.response?.data?.detail || 'Could not load profile'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const display = profile || {
    username: user?.username,
    full_name: user?.fullName,
    role: user?.role,
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="space-y-5">
      <PageHeader title="Settings" subtitle="Account and system information" />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6">
          <div className="flex flex-col items-center text-center">
            <span className="flex items-center justify-center w-20 h-20 rounded-full bg-blue-600 text-white text-2xl font-bold mb-4">
              {initials(display?.full_name || display?.username)}
            </span>
            <h3 className="text-lg font-semibold text-slate-900">{display?.full_name || display?.username}</h3>
            <p className="text-sm text-slate-500">{display?.username}</p>
            <span className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5" /> {String(display?.role || user?.role || 'User').toUpperCase()}
            </span>
          </div>
          <div className="mt-6">
            <button onClick={handleLogout} className="btn-danger w-full">
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </div>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="px-5 py-4 border-b border-slate-200 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <UserCircle className="w-4 h-4 text-blue-600" /> Account Profile
            </div>
            {loading ? (
              <div className="flex items-center justify-center gap-2 p-8 text-sm text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading profile...
              </div>
            ) : (
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5 p-6 text-sm">
                <div>
                  <dt className="text-xs text-slate-400 font-medium uppercase tracking-wide">Full Name</dt>
                  <dd className="mt-1 text-slate-800 font-medium">{display?.full_name || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400 font-medium uppercase tracking-wide">Username</dt>
                  <dd className="mt-1 text-slate-800 font-medium">{display?.username || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400 font-medium uppercase tracking-wide">Role</dt>
                  <dd className="mt-1 text-slate-800 font-medium capitalize">{display?.role || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400 font-medium uppercase tracking-wide">Account Status</dt>
                  <dd className="mt-1">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      {profile ? (profile.is_active === false ? 'Inactive' : 'Active') : 'Active'}
                    </span>
                  </dd>
                </div>
              </dl>
            )}
          </Card>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-100 text-slate-600">
                  <KeyRound className="w-4 h-4" />
                </span>
                <p className="text-sm font-semibold text-slate-900">Authentication</p>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">
                Signed in with a bearer token issued by the Allocation API. Session persists until you sign out or the
                token is revoked by an administrator.
              </p>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-100 text-slate-600">
                  <Database className="w-4 h-4" />
                </span>
                <p className="text-sm font-semibold text-slate-900">System</p>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">
                Allocator Asset Management · Laptop Allocation System. Laptop inventory, intern records and allocation
                history are managed through this dashboard.
              </p>
            </Card>
          </div>

          <Card className="p-5 flex items-start gap-3 text-sm text-slate-500">
            <Clock className="w-4 h-4 mt-0.5 text-slate-400 shrink-0" />
            <p>
              Profile access, laptops, interns, allocations and reports are protected routes. Only authenticated
              administrators can view or modify data.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Settings