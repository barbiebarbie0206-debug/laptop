import { useEffect, useState, useCallback } from 'react'
import { BarChart3, Download, FilterX, Loader2, FileText } from 'lucide-react'
import { allocationApi, getErrorMessage } from '../services/api'
import { PageHeader, SectionCard } from '../components/ui'
import { Card, LoadingSpinner, EmptyState, ErrorBanner, downloadBlob } from '../components/StateComponents'
import { BATCH_OPTIONS, DOMAIN_OPTIONS, ALLOCATION_STATUS_OPTIONS } from '../constants'

const emptyFilters = {
  allocation_date: '',
  batch: '',
  domain: '',
  laptop_number: '',
  intern_name: '',
  status: '',
}

function Reports() {
  const [filters, setFilters] = useState(emptyFilters)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  const buildParams = useCallback(() => {
    const params = {}
    Object.entries(filters).forEach(([k, v]) => {
      if (v && v.trim && v.trim() !== '') params[k] = typeof v === 'string' ? v.trim() : v
    })
    return params
  }, [filters])

  const load = useCallback(async () => {
    try {
      setError('')
      setLoading(true)
      const res = await allocationApi.getReports(buildParams())
      setReport(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [buildParams])

  useEffect(() => {
    load()
  }, [load])

  const hasActiveFilters = Object.values(filters).some((v) => v && v.trim && v.trim() !== '')

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const resetFilters = () => setFilters(emptyFilters)

  const handleExport = async () => {
    try {
      setExporting(true)
      const res = await allocationApi.exportCsv(buildParams())
      downloadBlob(res.data, 'allocations_report.csv')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  const summaryCards = report
    ? [
        { label: 'Total Allocations', value: report.total_allocations, tint: 'bg-blue-50 text-blue-600' },
        { label: 'Active', value: report.active_allocations, tint: 'bg-emerald-50 text-emerald-600' },
        { label: 'Returned', value: report.returned_allocations, tint: 'bg-sky-50 text-sky-600' },
        { label: 'Cancelled', value: report.cancelled_allocations, tint: 'bg-slate-100 text-slate-600' },
        { label: 'Unique Laptops Used', value: report.unique_laptops_used, tint: 'bg-indigo-50 text-indigo-600' },
        { label: 'Unique Interns', value: report.unique_interns, tint: 'bg-amber-50 text-amber-600' },
        { label: 'Free Laptops', value: report.free_laptops, tint: 'bg-emerald-50 text-emerald-600' },
      ]
    : []

  return (
    <div className="space-y-5">
      <PageHeader
        title="Reports"
        subtitle="Summary statistics with exportable data"
        actions={
          <button onClick={handleExport} disabled={exporting} className="btn-primary">
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {exporting ? 'Exporting...' : 'Export CSV'}
          </button>
        }
      />

      <ErrorBanner message={error} />

      <SectionCard
        title="Report Filters"
        actions={
          hasActiveFilters && (
            <button onClick={resetFilters} className="btn-ghost text-sm text-blue-600 hover:bg-blue-50">
              <FilterX className="w-4 h-4" /> Clear all
            </button>
          )
        }
        bodyClassName="p-4"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <div>
            <label className="label">Date</label>
            <input type="date" value={filters.allocation_date} onChange={(e) => updateFilter('allocation_date', e.target.value)} className="input" />
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
            <input value={filters.laptop_number} onChange={(e) => updateFilter('laptop_number', e.target.value)} placeholder="e.g. LP-001" className="input" />
          </div>
          <div>
            <label className="label">Intern</label>
            <input value={filters.intern_name} onChange={(e) => updateFilter('intern_name', e.target.value)} placeholder="Intern name" className="input" />
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

      {loading ? (
        <Card><LoadingSpinner /></Card>
      ) : report ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-4">
            {summaryCards.map((c) => (
              <div key={c.label} className="card p-5">
                <div className={`flex items-center justify-center w-10 h-10 rounded-lg ${c.tint} mb-3`}>
                  <BarChart3 className="w-5 h-5" />
                </div>
                <p className="text-2xl font-bold text-slate-900">{c.value}</p>
                <p className="text-sm font-medium text-slate-500 mt-1">{c.label}</p>
              </div>
            ))}
          </div>

          <SectionCard
            title="Domain-wise Breakdown"
            subtitle="Allocation totals per domain"
            actions={<span className="text-sm text-slate-500">Total: {report.total_allocations}</span>}
            bodyClassName="p-0"
          >
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="table-th">Domain</th>
                    <th className="table-th">Total</th>
                    <th className="table-th">Active</th>
                    <th className="table-th">Returned</th>
                    <th className="table-th">Cancelled</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-100">
                  {report.domain_stats.map((d) => (
                    <tr key={d.domain} className="hover:bg-slate-50">
                      <td className="table-td font-medium text-slate-800">{d.domain}</td>
                      <td className="table-td font-semibold text-slate-800">{d.total_allocations}</td>
                      <td className="table-td text-emerald-600">{d.active_allocations}</td>
                      <td className="table-td text-blue-600">{d.returned_allocations}</td>
                      <td className="table-td text-slate-500">{d.cancelled_allocations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <div className="card p-5 flex items-start gap-3 text-sm text-slate-500">
            <FileText className="w-4 h-4 mt-0.5 text-slate-400 shrink-0" />
            <p>
              Summary covers your current filter selection. Use “Export CSV” to download the underlying allocation records
              matching the same filters.
            </p>
          </div>
        </div>
      ) : null}

      {!loading && report && report.total_allocations === 0 && !hasActiveFilters && (
        <EmptyState title="No allocation data yet" message="Allocate laptops to generate report statistics" />
      )}
    </div>
  )
}

export default Reports