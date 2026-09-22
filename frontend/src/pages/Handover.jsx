import { useEffect, useState } from 'react'
import { Send, Undo2, XCircle, Loader2, ArrowLeftRight, PackageCheck, Inbox } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'
import { allocationApi, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import { notifyDataChanged } from '../services/events'
import ConfirmDialog from '../components/ConfirmDialog'
import StatusBadge from '../components/StatusBadge'
import { PageHeader, SectionCard, BatchBadge } from '../components/ui'
import { LoadingSpinner, EmptyState, ErrorBanner } from '../components/StateComponents'

const steps = [
  { icon: ArrowLeftRight, label: 'Allocate a laptop' },
  { icon: Send, label: 'Hand over the device' },
  { icon: PackageCheck, label: 'Complete on return' },
]

function Handover() {
  const navigate = useNavigate()
  const showToast = useToast()
  const [allocations, setAllocations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [actingId, setActingId] = useState(null)

  const load = async () => {
    try {
      setError('')
      const res = await allocationApi.getActive()
      setAllocations(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const complete = async (allocation, action) => {
    setActingId(allocation.id)
    try {
      if (action === 'return') {
        await allocationApi.returnLaptop(allocation.id)
        showToast(`${allocation.laptop_number} handed over / returned by ${allocation.intern_name}`)
      } else {
        await allocationApi.cancel(allocation.id)
        showToast(`Handover for ${allocation.laptop_number} cancelled`)
      }
      notifyDataChanged()
      setConfirm(null)
      load()
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
        title="Laptop Handover"
        subtitle="Track and complete device handover for active allocations"
        actions={
          <Link to="/allocate" className="btn-primary">
            <ArrowLeftRight className="w-4 h-4" /> New Allocation
          </Link>
        }
      />

      <div className="card p-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {steps.map((s, i) => (
          <div key={s.label} className="flex items-center gap-3">
            <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-50 text-blue-600 shrink-0">
              <s.icon className="w-5 h-5" />
            </span>
            <div>
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wide">Step {i + 1}</p>
              <p className="text-sm font-medium text-slate-800">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="card p-5">
          <p className="text-3xl font-bold text-slate-900">{allocations.length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Out to hand over</p>
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
          <p className="text-3xl font-bold text-slate-900">{allocations.length}</p>
          <p className="text-sm font-medium text-slate-500 mt-1">Awaiting return</p>
        </div>
      </div>

      <SectionCard
        title="Handover Queue"
        subtitle="Laptops currently issued — complete the handover by recording the return"
        bodyClassName="p-0"
      >
        {loading ? (
          <LoadingSpinner />
        ) : allocations.length === 0 ? (
          <EmptyState
            title="Nothing to hand over right now"
            message="Allocate a laptop first, then hand it over to the intern"
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
                  <th className="table-th">End Time</th>
                  <th className="table-th">Status</th>
                  <th className="table-th text-right">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {allocations.map((alloc) => (
                  <tr key={alloc.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{alloc.laptop_number}</td>
                    <td className="table-td text-slate-800">{alloc.intern_name}</td>
                    <td className="table-td"><BatchBadge batch={alloc.batch} /></td>
                    <td className="table-td">{alloc.start_time}</td>
                    <td className="table-td">{alloc.end_time}</td>
                    <td className="table-td"><StatusBadge status={alloc.status} /></td>
                    <td className="table-td">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setConfirm({ allocation: alloc, action: 'return' })}
                          disabled={actingId === alloc.id}
                          className="btn-success px-3 py-1.5 text-xs"
                        >
                          {actingId === alloc.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PackageCheck className="w-3.5 h-3.5" />}
                          Complete
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

      <div className="flex justify-end">
        <button onClick={() => navigate('/inover')} className="btn-secondary">
          <Inbox className="w-4 h-4" /> Go to Inover
        </button>
      </div>

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.action === 'cancel' ? 'Cancel Handover' : 'Complete Handover'}
        message={
          confirm
            ? confirm.action === 'cancel'
              ? `Cancel the handover of ${confirm.allocation.laptop_number} (${confirm.allocation.intern_name})? The laptop will return to the free pool.`
              : `Mark laptop ${confirm.allocation.laptop_number} as collected back from ${confirm.allocation.intern_name}? The device will return to the free pool.`
            : ''
        }
        confirmLabel={confirm?.action === 'cancel' ? 'Cancel' : 'Complete Handover'}
        danger={confirm?.action === 'cancel'}
        loading={actingId === confirm?.allocation?.id}
        onConfirm={() => confirm && complete(confirm.allocation, confirm.action)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}

export default Handover