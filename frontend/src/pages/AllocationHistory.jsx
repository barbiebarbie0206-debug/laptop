import { useEffect, useState, useCallback } from 'react'
import { Search, Download, FilterX, History as HistoryIcon, Loader2 } from 'lucide-react'
import { allocationApi, getErrorMessage } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import { PageHeader, SectionCard, BatchBadge } from '../components/ui'
import { Card, LoadingSpinner, EmptyState, ErrorBanner, downloadBlob } from '../components/StateComponents'
import { BATCH_OPTIONS, DOMAIN_OPTIONS, ALLOCATION_STATUS_OPTIONS } from '../constants'

const emptyFilters = {
  allocation_date: '',
  batch: '',
  domain: '',
  laptop_number: '',
  intern_name: '',
  status: '',
  search: '',
}

function AllocationHistory() {
  const [filters, setFilters] = useState(emptyFilters)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  const buildParams = useCallback((pg, ps) => {
    const params = { page: pg, page_size: ps }
    Object.entries(filters).forEach(([k, v]) => {
      if (v && v.trim && v.trim() !== '') params[k] = typeof v === 'string' ? v.trim() : v
    })
    return params
  }, [filters])

  const load = useCallback(async (pg = page, ps = pageSize) => {
    try {
      setError('')
      setLoading(true)
      const res = await allocationApi.getHistory(buildParams(pg, ps))
      setItems(res.data.items)
      setTotal(res.data.total)
      setTotalPages(res.data.total_pages)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, buildParams])

  useEffect(() => {
    load(page, pageSize)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, filters])

  const hasActiveFilters = Object.values(filters).some((v) => v && v.trim && v.trim() !== '')

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const resetFilters = () => {
    setFilters(emptyFilters)
    setPage(1)
  }

  const handleExport = async () => {
    try {
      setExporting(true)
      const res = await allocationApi.exportCsv(buildParams(1, 100000))
      downloadBlob(res.data, 'allocations_export.csv')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Allocation History"
        subtitle="All recorded laptop allocations with search and filters"
        actions={
          <button onClick={handleExport} disabled={exporting} className="btn-primary">
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {exporting ? 'Exporting...' : 'Export CSV'}
          </button>
        }
      />

      <ErrorBanner message={error} />

      <SectionCard
        title="Search & Filters"
        subtitle={hasActiveFilters ? 'Filters applied' : 'Narrow down the allocation history'}
        actions={
          hasActiveFilters && (
            <button onClick={resetFilters} className="btn-ghost text-sm text-blue-600 hover:bg-blue-50">
              <FilterX className="w-4 h-4" /> Clear all filters
            </button>
          )
        }
        bodyClassName="p-4 space-y-3"
      >
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
            placeholder="Search by laptop number or intern name..."
            className="input pl-9"
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <div>
            <label className="label">Date</label>
            <input
              type="date"
              value={filters.allocation_date}
              onChange={(e) => updateFilter('allocation_date', e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="label">Batch</label>
            <select value={filters.batch} onChange={(e) => updateFilter('batch', e.target.value)} className="input">
              <option value="">All</option>
              {BATCH_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Domain</label>
            <select value={filters.domain} onChange={(e) => updateFilter('domain', e.target.value)} className="input">
              <option value="">All</option>
              {DOMAIN_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Laptop</label>
            <input
              value={filters.laptop_number}
              onChange={(e) => updateFilter('laptop_number', e.target.value)}
              placeholder="e.g. LP-001"
              className="input"
            />
          </div>
          <div>
            <label className="label">Intern</label>
            <input
              value={filters.intern_name}
              onChange={(e) => updateFilter('intern_name', e.target.value)}
              placeholder="Intern name"
              className="input"
            />
          </div>
          <div>
            <label className="label">Status</label>
            <select value={filters.status} onChange={(e) => updateFilter('status', e.target.value)} className="input">
              <option value="">All</option>
              {ALLOCATION_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
      </SectionCard>

      <Card>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <HistoryIcon className="w-4 h-4 text-blue-600" /> Allocations
          </div>
          <span className="text-sm text-slate-500">{total} result{total === 1 ? '' : 's'}</span>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : items.length === 0 ? (
          <EmptyState
            title="No allocations found"
            message={hasActiveFilters ? 'Try adjusting your search or filters' : 'Allocate a laptop to see history here'}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Laptop</th>
                  <th className="table-th">Intern</th>
                  <th className="table-th">Batch</th>
                  <th className="table-th">Domain</th>
                  <th className="table-th">Allocation Date</th>
                  <th className="table-th">Start Time</th>
                  <th className="table-th">End Time</th>
                  <th className="table-th">Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {items.map((alloc) => (
                  <tr key={alloc.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{alloc.laptop_number}</td>
                    <td className="table-td text-slate-800">{alloc.intern_name}</td>
                    <td className="table-td"><BatchBadge batch={alloc.batch} /></td>
                    <td className="table-td">{alloc.domain}</td>
                    <td className="table-td">{alloc.allocation_date}</td>
                    <td className="table-td">{alloc.start_time}</td>
                    <td className="table-td">{alloc.end_time}</td>
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
      </Card>
    </div>
  )
}

export default AllocationHistory