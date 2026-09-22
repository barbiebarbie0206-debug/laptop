import { useEffect, useRef, useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Laptop,
  Users,
  ArrowLeftRight,
  Activity,
  Send,
  Inbox,
  History,
  BarChart3,
  Settings,
  Search,
  Bell,
  LogOut,
  Menu,
  X,
  ChevronDown,
  ShieldCheck,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { laptopApi, internApi, allocationApi } from '../services/api'

const navSections = [
  {
    label: 'Overview',
    items: [{ path: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }],
  },
  {
    label: 'Management',
    items: [
      { path: '/laptops', label: 'Laptops', icon: Laptop },
      { path: '/interns', label: 'Interns', icon: Users },
    ],
  },
  {
    label: 'Allocations',
    items: [
      { path: '/allocate', label: 'Allocate Laptop', icon: ArrowLeftRight },
      { path: '/allocations', label: 'Active Allocations', icon: Activity },
      { path: '/handover', label: 'Handover', icon: Send },
      { path: '/inover', label: 'Inover', icon: Inbox },
      { path: '/allocations/history', label: 'Allocation History', icon: History },
    ],
  },
  {
    label: 'Insights',
    items: [{ path: '/reports', label: 'Reports', icon: BarChart3 }],
  },
  {
    label: 'System',
    items: [{ path: '/settings', label: 'Settings', icon: Settings }],
  },
]

function initials(name) {
  const parts = String(name || 'U').split(' ').filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || 'U'
}

function Logo() {
  return (
    <NavLink to="/" className="flex items-center gap-3 px-5 h-16 shrink-0">
      <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-lg shadow-blue-900/40">
        <Laptop className="w-5 h-5" />
      </span>
      <span className="leading-tight">
        <span className="block text-[15px] font-bold text-white tracking-tight">Allocator</span>
        <span className="block text-[11px] text-blue-300/80">Asset Management</span>
      </span>
    </NavLink>
  )
}

function useGlobalSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState({ laptops: [], interns: [] })
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const q = query.trim()
    if (q.length < 1) {
      setResults({ laptops: [], interns: [] })
      setOpen(false)
      return undefined
    }
    const timer = setTimeout(async () => {
      try {
        const [laps, ints] = await Promise.all([
          laptopApi.getAll({ search: q, limit: 5 }),
          internApi.getAll({ search: q, limit: 5 }),
        ])
        setResults({ laptops: laps.data || [], interns: ints.data || [] })
        setOpen(true)
      } catch {
        setResults({ laptops: [], interns: [] })
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  return { query, setQuery, results, open, setOpen }
}

function GlobalSearch() {
  const navigate = useNavigate()
  const { query, setQuery, results, open, setOpen } = useGlobalSearch()
  const boxRef = useRef(null)
  const hasResults = results.laptops.length > 0 || results.interns.length > 0

  const go = (path) => {
    setOpen(false)
    setQuery('')
    navigate(path)
  }

  return (
    <div ref={boxRef} className="relative flex-1 max-w-md">
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (query.trim()) setOpen(true) }}
          placeholder="Search laptops, interns, records..."
          className="w-full pl-9 pr-4 py-2 text-sm bg-slate-100 hover:bg-slate-200/70 border border-transparent focus:bg-white focus:border-slate-300 rounded-lg placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-colors"
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setOpen(false) }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {open && query.trim() && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute z-20 mt-2 w-full card shadow-popover overflow-hidden animate-fade-up">
            {!hasResults && (
              <div className="px-4 py-6 text-center text-sm text-slate-400">
                No results for “{query}”
              </div>
            )}
            {results.laptops.length > 0 && (
              <div>
                <p className="px-4 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Laptops</p>
                {results.laptops.slice(0, 5).map((l) => (
                  <button
                    key={l.id}
                    onClick={() => go(`/laptops?q=${encodeURIComponent(query)}`)}
                    className="w-full text-left px-4 py-2 hover:bg-slate-50 flex items-center gap-3"
                  >
                    <Laptop className="w-4 h-4 text-slate-400" />
                    <span>
                      <span className="block text-sm text-slate-800 font-medium">{l.laptop_number}</span>
                      <span className="block text-xs text-slate-400">{l.brand} {l.model}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
            {results.interns.length > 0 && (
              <div>
                <p className="px-4 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Interns</p>
                {results.interns.slice(0, 5).map((i) => (
                  <button
                    key={i.id}
                    onClick={() => go(`/interns?q=${encodeURIComponent(query)}`)}
                    className="w-full text-left px-4 py-2 hover:bg-slate-50 flex items-center gap-3"
                  >
                    <Users className="w-4 h-4 text-slate-400" />
                    <span>
                      <span className="block text-sm text-slate-800 font-medium">{i.name}</span>
                      <span className="block text-xs text-slate-400">{i.intern_id} · {i.domain}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
            <div className="px-4 py-2.5 border-t border-slate-200 text-xs text-slate-400">
              Press to jump to results in Laptops / Interns
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Notifications() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    const load = async () => {
      try {
        const [active, returned, cancelledRes] = await Promise.all([
          allocationApi.getActive(),
          allocationApi.getHistory({ page: 1, page_size: 1, status: 'RETURNED' }),
          allocationApi.getHistory({ page: 1, page_size: 1, status: 'CANCELLED' }),
        ])
        if (!cancelled) {
          setData({
            active: active.data.length || 0,
            returned: returned.data.total || 0,
            cancelled: cancelledRes.data.total || 0,
          })
        }
      } catch {
        if (!cancelled) setData(null)
      }
    }
    load()
    return () => { cancelled = true }
  }, [open])

  const count = data?.active || 0

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
        title="Notifications"
      >
        <Bell className="w-5 h-5" />
        {count > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600" />
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-72 card shadow-popover overflow-hidden animate-fade-up">
            <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-900">Notifications</p>
              <button onClick={() => setOpen(false)}><X className="w-4 h-4 text-slate-400 hover:text-slate-600" /></button>
            </div>
            <div className="py-2">
              {!data ? (
                <p className="px-4 py-4 text-sm text-slate-400 text-center">Loading...</p>
              ) : (
                <>
                  <button
                    onClick={() => { setOpen(false); navigate('/allocations') }}
                    className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3"
                  >
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50 text-blue-600"><Activity className="w-4 h-4" /></span>
                    <span>
                      <span className="block text-sm text-slate-800">{data.active} active allocation{data.active === 1 ? '' : 's'}</span>
                      <span className="block text-xs text-slate-400">Laptops currently issued</span>
                    </span>
                  </button>
                  <button
                    onClick={() => { setOpen(false); navigate('/inover') }}
                    className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3"
                  >
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600"><Inbox className="w-4 h-4" /></span>
                    <span>
                      <span className="block text-sm text-slate-800">{data.returned} returned · {data.cancelled} cancelled</span>
                      <span className="block text-xs text-slate-400">Laptops received back</span>
                    </span>
                  </button>
                  <button
                    onClick={() => { setOpen(false); navigate('/allocations/history') }}
                    className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3"
                  >
                    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 text-slate-500"><History className="w-4 h-4" /></span>
                    <span className="text-sm text-blue-600 font-medium">View full history</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ProfileMenu() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  const handleLogout = () => {
    setOpen(false)
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 pl-1 pr-2 py-1 rounded-lg hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center justify-center w-9 h-9 rounded-full bg-blue-600 text-white text-sm font-bold">
          {initials(user?.fullName || user?.username)}
        </span>
        <span className="hidden sm:block text-left">
          <span className="block text-sm font-medium text-slate-800 leading-tight">{user?.fullName || user?.username}</span>
          <span className="block text-xs text-slate-400 capitalize leading-tight">{user?.role}</span>
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-56 card shadow-popover overflow-hidden animate-fade-up">
            <div className="px-4 py-3 border-b border-slate-200">
              <p className="text-sm font-semibold text-slate-900 truncate">{user?.fullName || user?.username}</p>
              <p className="text-xs text-slate-400 truncate">{user?.username}</p>
            </div>
            <div className="py-1.5">
              <button
                onClick={() => { setOpen(false); navigate('/settings') }}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2.5"
              >
                <Settings className="w-4 h-4 text-slate-400" /> Account Settings
              </button>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2.5"
              >
                <LogOut className="w-4 h-4" /> Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function SidebarContent({ onNavigate }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="flex flex-col h-full bg-navy-900">
      <Logo />
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">{section.label}</p>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-950/50'
                        : 'text-slate-400 hover:bg-white/5 hover:text-white'
                    }`
                  }
                >
                  <item.icon className="w-[18px] h-[18px] shrink-0" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="p-3 border-t border-white/10">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg bg-white/5">
          <span className="flex items-center justify-center w-9 h-9 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0">
            {initials(user?.fullName || user?.username)}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.fullName || user?.username}</p>
            <p className="text-xs text-slate-400 capitalize flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 inline" /> {user?.role || 'user'}
            </p>
          </div>
          <button
            onClick={() => { logout(); navigate('/login', { replace: true }) }}
            title="Sign out"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex h-screen overflow-hidden">
        <aside className="hidden lg:block w-64 shrink-0 bg-navy-900">
          <SidebarContent />
        </aside>

        {mobileOpen && (
          <>
            <div className="fixed inset-0 z-40 bg-slate-900/60 lg:hidden animate-fade-in" onClick={() => setMobileOpen(false)} />
            <aside className="fixed inset-y-0 left-0 z-50 w-64 lg:hidden">
              <SidebarContent onNavigate={() => setMobileOpen(false)} />
            </aside>
          </>
        )}

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <header className="flex items-center gap-3 h-16 bg-white border-b border-slate-200 px-4 lg:px-6 shrink-0">
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 lg:hidden"
              title="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <GlobalSearch />
            <div className="flex-1" />
            <Notifications />
            <ProfileMenu />
          </header>

          <main className="flex-1 overflow-y-auto p-4 lg:p-6">
            <div className="max-w-[1400px] mx-auto">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}