import { useEffect, useState } from 'react'
import { Activity, Undo2, XCircle, RefreshCw, Loader2 } from 'lucide-react'
import { allocationApi, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import { notifyDataChanged } from '../services/events'
import ConfirmDialog from '../components/ConfirmDialog'
import StatusBadge from '../components/StatusBadge'
import { PageHeader, SectionCard, BatchBadge } from '../components/ui'
import { LoadingSpinner, EmptyState, ErrorBanner } from '../components/StateComponents'

function ActiveAllocations() {
  const [allocations, setAllocations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [actingId, setActingId] = useState(null)
  const showToast = useToast()

  const loadActive = async () => {
    try {
      setError('')
      const response = await allocationApi.getActive()
      setAllocations(Array.isArray(response.data) ? response.data : [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadActive()
  }, [])

  const runAction = async (allocation, action) => {
    setActingId(allocation.id)
    try {
      if (action === 'return') {
        await allocationApi.returnLaptop(allocation.id)
        showToast(`Laptop ${allocation.laptop_number} marked as returned`)
      } else {
        await allocationApi.cancel(allocation.id)
        showToast(`Allocation for ${allocation.laptop_number} cancelled`)
      }
      notifyDataChanged()
      setConfirm(null)
      loadActive()
    } catch (err) {
      showToast(getErrorMessage(err), 'error')
      setConfirm(null)
    } finally {
      setActingId(null)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Active Allocations"
        subtitle="Laptops currently allocated to interns"
        actions={
          <button onClick={loadActive} className="btn-secondary" disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        }
      />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{allocations.length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Active</p>
        </div>
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{allocations.filter((a) => a.batch === 'Morning').length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Morning batch</p>
        </div>
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{allocations.filter((a) => a.batch === 'Afternoon').length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Afternoon batch</p>
        </div>
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{allocations.filter((a) => a.batch === 'Full Day').length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Full Day batch</p>
        </div>
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{new Set(allocations.map((a) => a.domain)).size}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Domains covered</p>
        </div>
      </div>

      <SectionCard
        title="Currently Active"
        subtitle="Allocate, return or cancel from here"
        actions={
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
            <Activity className="w-3.5 h-3.5" /> Live
          </span>
        }
        bodyClassName="p-0"
      >
        {loading ? (
          <LoadingSpinner />
        ) : allocations.length === 0 ? (
          <EmptyState title="No active allocations right now" message="Allocate a laptop to an intern to see it here" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Laptop</th>
                  <th className="table-th">Intern</th>
                  <th className="table-th">Batch</th>
                  <th className="table-th">Domain</th>
                  <th className="table-th">Start Time</th>
                  <th className="table-th">Status</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {allocations.map((alloc) => (
                  <tr key={alloc.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{alloc.laptop_number}</td>
                    <td className="table-td text-slate-800">{alloc.intern_name}</td>
                    <td className="table-td"><BatchBadge batch={alloc.batch} /></td>
                    <td className="table-td">{alloc.domain}</td>
                    <td className="table-td">{alloc.start_time}</td>
                    <td className="table-td"><StatusBadge status={alloc.status} /></td>
                    <td className="table-td">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setConfirm({ allocation: alloc, action: 'return' })}
                          disabled={actingId === alloc.id}
                          className="btn-success px-3 py-1.5 text-xs"
                        >
                          {actingId === alloc.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Undo2 className="w-3.5 h-3.5" />}
                          Return
                        </button>
                        <button
                          onClick={() => setConfirm({ allocation: alloc, action: 'cancel' })}
                          disabled={actingId === alloc.id}
                          className="btn-ghost px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.action === 'return' ? 'Return Laptop' : 'Cancel Allocation'}
        message={
          confirm
            ? `Are you sure you want to ${
                confirm.action === 'return' ? 'return' : 'cancel'
              } laptop ${confirm.allocation.laptop_number} (${confirm.allocation.intern_name})?`
            : ''
        }
        confirmLabel={confirm?.action === 'return' ? 'Return' : 'Cancel Allocation'}
        danger={confirm?.action === 'cancel'}
        loading={actingId === confirm?.allocation?.id}
        onConfirm={() => confirm && runAction(confirm.allocation, confirm.action)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}

export default ActiveAllocations