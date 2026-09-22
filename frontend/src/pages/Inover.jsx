import { useEffect, useState, useCallback } from 'react'
import { Inbox, Search, RefreshCw, Undo2, XCircle, Send } from 'lucide-react'
import { Link } from 'react-router-dom'
import { allocationApi, getErrorMessage } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import { PageHeader, SectionCard, BatchBadge } from '../components/ui'
import { LoadingSpinner, EmptyState, ErrorBanner } from '../components/StateComponents'

const tabs = [
  { value: '', label: 'All received' },
  { value: 'RETURNED', label: 'Returned' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

function Inover() {
  const [tab, setTab] = useState('')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async (pg = page, ps = pageSize, status = tab, q = search) => {
    try {
      setError('')
      setLoading(true)
      const params = { page: pg, page_size: ps, status: status || undefined }
      if (q.trim()) params.search = q.trim()
      const res = await allocationApi.getHistory(params)
      setItems(Array.isArray(res.data.items) ? res.data.items : [])
      setTotal(res.data.total || 0)
      setTotalPages(res.data.total_pages || 0)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, tab, search])

  useEffect(() => {
    load(page, pageSize, tab, search)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, tab, search])

  const switchTab = (value) => {
    setTab(value)
    setPage(1)
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Laptop Inover"
        subtitle="Devices received back — returned or cancelled allocations"
        actions={
          <Link to="/handover" className="btn-secondary">
            <Send className="w-4 h-4" /> Go to Handover
          </Link>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-5 flex items-center gap-4">
          <span className="flex items-center justify-center w-11 h-11 rounded-xl bg-blue-50 text-blue-600"><Inbox className="w-5 h-5" /></span>
          <div>
            <p className="text-2xl font-bold text-slate-900">{total}</p>
            <p className="text-sm font-medium text-slate-500">Received back</p>
          </div>
        </div>
        <div className="card p-5 flex items-center gap-4">
          <span className="flex items-center justify-center w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600"><Undo2 className="w-5 h-5" /></span>
          <div>
            <p className="text-2xl font-bold text-slate-900">{total}</p>
            <p className="text-sm font-medium text-slate-500">Returned to date</p>
          </div>
        </div>
        <div className="card p-5 flex items-center gap-4">
          <span className="flex items-center justify-center w-11 h-11 rounded-xl bg-slate-100 text-slate-600"><XCircle className="w-5 h-5" /></span>
          <div>
            <p className="text-2xl font-bold text-slate-900">{total}</p>
            <p className="text-sm font-medium text-slate-500">In this view</p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="p-4 flex flex-col sm:flex-row gap-3 items-stretch justify-between border-b border-slate-200">
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            {tabs.map((t) => (
              <button
                key={t.value}
                onClick={() => switchTab(t.value)}
                className={`px-3.5 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  tab === t.value ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search laptop or intern..."
              className="input pl-9"
            />
          </div>
        </div>

        <ErrorBanner message={error} />

        {loading ? (
          <LoadingSpinner />
        ) : items.length === 0 ? (
          <EmptyState
            title="No received devices"
            message={search ? 'Try a different search term' : 'Returned and cancelled allocations will appear here'}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Laptop</th>
                  <th className="table-th">Intern</th>
                  <th className="table-th">Batch</th>
                  <th className="table-th">Start Time</th>
                  <th className="table-th">Allocation Date</th>
                  <th className="table-th">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {items.map((alloc) => (
                  <tr key={alloc.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{alloc.laptop_number}</td>
                    <td className="table-td text-slate-800">{alloc.intern_name}</td>
                    <td className="table-td"><BatchBadge batch={alloc.batch} /></td>
                    <td className="table-td">{alloc.start_time}</td>
                    <td className="table-td">{alloc.allocation_date}</td>
                    <td className="table-td"><StatusBadge status={alloc.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </div>

      <div className="flex justify-end">
        <button onClick={() => load()} className="btn-secondary">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>
    </div>
  )
}

export default Inover