import { useEffect, useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Laptop,
  CheckCircle2,
  ArrowLeftRight,
  Undo2,
  ShieldCheck,
  Users,
  Send,
  Inbox,
  ClipboardList,
  ChevronRight,
  Loader2,
  BarChart3,
  UserPlus,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { dashboardApi, allocationApi, internApi, getErrorMessage } from '../services/api'
import { subscribeDataChanged } from '../services/events'
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/StateComponents'
import StatusBadge from '../components/StatusBadge'
import ExcelImport from '../components/ExcelImport'
import { SectionCard, BatchBadge, StatCard } from '../components/ui'
import { useAuth } from '../context/AuthContext'

const STATUS_COLORS = {
  Free: '#10b981',
  Allocated: '#3b82f6',
  Maintenance: '#f59e0b',
  Inactive: '#94a3b8',
}

const tooltipStyle = {
  borderRadius: 10,
  border: '1px solid #e2e8f0',
  boxShadow: '0 8px 24px -6px rgba(15,23,42,0.14)',
  fontSize: 13,
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function formatMonth(key) {
  if (!key) return key
  const [y, m] = key.split('-')
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${names[Number(m) - 1]} ${y.slice(2)}`
}

function Clock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  const date = now.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const time = now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500 tabular-nums">
      <span>{date}</span>
      <span className="text-slate-300">·</span>
      <span>{time}</span>
    </span>
  )
}

function SystemStatus() {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium ring-1 ring-emerald-200">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-70" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      System Online
    </span>
  )
}

function AllocationTrendChart({ data }) {
  if (!data || data.length === 0) {
    return <EmptyState title="No allocation trend yet" message="Allocation history will appear here as records are created" />
  }
  const chartData = data.map((d) => ({ ...d, month: formatMonth(d.month) }))
  return (
    <div className="w-full h-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 12, left: -14, bottom: 0 }}>
          <defs>
            <linearGradient id="allocGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.18} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="retGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.18} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <ReTooltip contentStyle={tooltipStyle} cursor={{ stroke: '#cbd5e1' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area type="monotone" dataKey="allocated" name="Allocated" stroke="#3b82f6" strokeWidth={2} fill="url(#allocGrad)" />
          <Area type="monotone" dataKey="returned" name="Returned" stroke="#10b981" strokeWidth={2} fill="url(#retGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function StatusDistributionChart({ data }) {
  const shown = (data || []).filter((d) => d.value > 0)
  if (shown.length === 0) {
    return <EmptyState title="No laptop data" message="Add laptops to see the status distribution" />
  }
  return (
    <div className="w-full h-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={shown}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={82}
            innerRadius={50}
            paddingAngle={2}
          >
            {shown.map((entry) => (
              <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#94a3b8'} stroke="none" />
            ))}
          </Pie>
          <ReTooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [interns, setInterns] = useState([])
  const [inoverCount, setInoverCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      const [statsRes, histRes, internsRes, retRes, canRes] = await Promise.all([
        dashboardApi.getStats(),
        allocationApi.getHistory({ page: 1, page_size: 5 }),
        internApi.getAll({ limit: 6 }),
        allocationApi.getHistory({ page: 1, page_size: 1, status: 'RETURNED' }),
        allocationApi.getHistory({ page: 1, page_size: 1, status: 'CANCELLED' }),
      ])
      setStats(statsRes.data)
      setRecent(Array.isArray(histRes.data?.items) ? histRes.data.items : [])
      setInterns(Array.isArray(internsRes.data) ? internsRes.data : [])
      setInoverCount((retRes.data?.total || 0) + (canRes.data?.total || 0))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  useEffect(() => subscribeDataChanged(load), [load])

  const statusData = (stats?.laptop_status_distribution || []).filter((d) => d.value > 0)

  const quickActions = [
    { label: 'Allocate Laptop', note: 'Issue a laptop to an intern', icon: ArrowLeftRight, to: '/allocate', tint: 'bg-emerald-50 text-emerald-600', arrow: true },
    { label: 'View Laptops', note: 'Browse the inventory', icon: Laptop, to: '/laptops', tint: 'bg-blue-50 text-blue-600' },
    { label: 'Manage Interns', note: 'Add or edit interns', icon: UserPlus, to: '/interns', tint: 'bg-indigo-50 text-indigo-600' },
    { label: 'View Reports', note: 'Insights and exports', icon: BarChart3, to: '/reports', tint: 'bg-amber-50 text-amber-600' },
  ]

  const totalLaptops = stats?.total_laptops ?? 0
  const freePct = totalLaptops ? Math.round(((stats?.free_laptops ?? 0) / totalLaptops) * 100) : 0
  const allocPct = totalLaptops ? Math.round(((stats?.allocated_laptops ?? 0) / totalLaptops) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">
              {greeting()}, {user?.fullName || user?.username}
            </h1>
            <SystemStatus />
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Here&apos;s what&apos;s happening with your laptop allocation system today.
          </p>
          <p className="text-xs text-slate-400 mt-2">
            <Clock />
          </p>
        </div>
      </div>

      <ErrorBanner message={error} />

      {loading && !stats ? (
        <LoadingSpinner className="w-12 h-12" />
      ) : stats && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
            <StatCard
              icon={<Laptop className="w-5 h-5" />}
              label="Total Laptops"
              value={stats.total_laptops ?? 0}
              hint="In inventory"
              iconClass="bg-blue-50 text-blue-600"
            />
            <StatCard
              icon={<CheckCircle2 className="w-5 h-5" />}
              label="Free Laptops"
              value={stats.free_laptops ?? 0}
              hint="Available now"
              trend={`${freePct}% of inventory`}
              iconClass="bg-emerald-50 text-emerald-600"
            />
            <StatCard
              icon={<ArrowLeftRight className="w-5 h-5" />}
              label="Allocated Laptops"
              value={stats.allocated_laptops ?? 0}
              hint="Currently allocated"
              trend={`${allocPct}% of inventory`}
              iconClass="bg-indigo-50 text-indigo-600"
            />
            <StatCard
              icon={<Undo2 className="w-5 h-5" />}
              label="Returned Laptops"
              value={stats.returned_allocations ?? 0}
              hint="Returned to date"
              iconClass="bg-sky-50 text-sky-600"
            />
            <StatCard
              icon={<Users className="w-5 h-5" />}
              label="Total Interns"
              value={stats.total_interns ?? 0}
              hint="Registered"
              iconClass="bg-slate-100 text-slate-600"
            />
            <StatCard
              icon={<ShieldCheck className="w-5 h-5" />}
              label="Active Allocations"
              value={stats.active_allocations ?? 0}
              hint="Currently issued"
              iconClass="bg-violet-50 text-violet-600"
            />
          </div>

          {/* Excel Import / Export */}
          <ExcelImport />

          {/* Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <SectionCard
              title="Laptop Allocation Trend"
              subtitle="Allocated vs returned per month"
              className="lg:col-span-2"
              bodyClassName="p-5 h-80"
            >
              <AllocationTrendChart data={stats.allocation_trend || []} />
            </SectionCard>

            <SectionCard
              title="Laptop Status Distribution"
              subtitle="Current inventory split"
              bodyClassName="p-5 h-80"
            >
              <StatusDistributionChart data={statusData} />
            </SectionCard>
          </div>

          {/* Quick Actions */}
          <SectionCard title="Quick Actions" subtitle="Common tasks" bodyClassName="p-5">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {quickActions.map((a) => (
                <button
                  key={a.label}
                  onClick={() => navigate(a.to)}
                  className="group flex items-center gap-3 p-4 rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-card-hover transition-all text-left"
                >
                  <span className={`flex items-center justify-center w-10 h-10 rounded-xl shrink-0 ${a.tint}`}>
                    <a.icon className="w-5 h-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-slate-800 group-hover:text-blue-700 truncate">{a.label}</span>
                    <span className="block text-xs text-slate-400 truncate">{a.note}</span>
                  </span>
                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 ml-auto shrink-0" />
                </button>
              ))}
            </div>
          </SectionCard>

          {/* Handover / Inover */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-blue-50 text-blue-600">
                  <Send className="w-6 h-6" />
                </span>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{stats.active_allocations ?? 0}</p>
                  <p className="text-sm font-medium text-slate-500">Laptops handed over</p>
                  <p className="text-xs text-slate-400 mt-0.5">Currently issued and active</p>
                </div>
              </div>
              <Link to="/handover" className="btn-secondary">
                Manage <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="card p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600">
                  <Inbox className="w-6 h-6" />
                </span>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{inoverCount}</p>
                  <p className="text-sm font-medium text-slate-500">Laptops received back</p>
                  <p className="text-xs text-slate-400 mt-0.5">Returned or cancelled to date</p>
                </div>
              </div>
              <Link to="/inover" className="btn-secondary">
                View <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {/* Recent + Latest interns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SectionCard
              title="Recent Allocations"
              subtitle="Latest allocation activity"
              actions={
                <Link to="/allocations/history" className="text-sm font-medium text-blue-600 hover:text-blue-700 inline-flex items-center gap-1">
                  View all <ChevronRight className="w-4 h-4" />
                </Link>
              }
              bodyClassName="p-0"
            >
              {recent.length === 0 ? (
                <EmptyState title="No allocations yet" message="Allocate a laptop to an intern to see recent activity" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="table-th">Laptop</th>
                        <th className="table-th">Intern</th>
                        <th className="table-th">Batch</th>
                        <th className="table-th">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {recent.map((a) => (
                        <tr key={a.id} className="hover:bg-slate-50">
                          <td className="table-td font-medium text-slate-800">{a.laptop_number}</td>
                          <td className="table-td text-slate-800">{a.intern_name}</td>
                          <td className="table-td"><BatchBadge batch={a.batch} /></td>
                          <td className="table-td"><StatusBadge status={a.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard
              title="Latest Interns"
              subtitle="Recently registered interns"
              actions={
                <Link to="/interns" className="text-sm font-medium text-blue-600 hover:text-blue-700 inline-flex items-center gap-1">
                  View all <ChevronRight className="w-4 h-4" />
                </Link>
              }
              bodyClassName="p-0"
            >
              {interns.length === 0 ? (
                <EmptyState title="No interns yet" message="Add an intern to get started" />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {interns.map((i) => (
                    <li key={i.id} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50">
                      <span className="flex items-center justify-center w-9 h-9 rounded-full bg-blue-50 text-blue-700 text-xs font-bold shrink-0">
                        {String(i.name || '?').split(' ').filter(Boolean).map((p) => p[0]).slice(0, 2).join('').toUpperCase()}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{i.name}</p>
                        <p className="text-xs text-slate-400 truncate">{i.intern_id}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs text-slate-500">{i.domain}</p>
                        <BatchBadge batch={i.batch} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </SectionCard>
          </div>
        </>
      )}
    </div>
  )
}

export default Dashboard