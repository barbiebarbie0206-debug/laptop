import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Search, Edit2, Eye, Power, Laptop as LaptopIcon, Loader2, Info } from 'lucide-react'
import { laptopApi, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import { notifyDataChanged, subscribeDataChanged } from '../services/events'
import StatusBadge from '../components/StatusBadge'
import { PageHeader, Modal } from '../components/ui'
import { Card, LoadingSpinner, EmptyState, ErrorBanner } from '../components/StateComponents'
import ExcelImport from '../components/ExcelImport'

const FILTER_STATUS_OPTIONS = ['FREE', 'ALLOCATED', 'RETURNED', 'MAINTENANCE', 'INACTIVE']
const FORM_STATUS_OPTIONS = ['FREE', 'ALLOCATED', 'MAINTENANCE', 'INACTIVE']

const emptyForm = {
  laptop_number: '',
  brand: '',
  model: '',
  serial_number: '',
  status: 'FREE',
}

function Laptops() {
  const navigate = useNavigate()
  const location = useLocation()
  const showToast = useToast()

  const initialQuery = new URLSearchParams(location.search).get('q') || ''

  const [laptops, setLaptops] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState(initialQuery)
  const [statusFilter, setStatusFilter] = useState('')
  const [internWithoutLaptop, setInternWithoutLaptop] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [viewing, setViewing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (new URLSearchParams(location.search).get('add') === '1') {
      setModalOpen(true)
      const qs = initialQuery ? `?q=${encodeURIComponent(initialQuery)}` : ''
      navigate(location.pathname + qs, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadLaptops = async () => {
    try {
      setLoading(true)
      const params = { envelope: true }
      if (search.trim()) params.search = search.trim()
      if (statusFilter) params.status = statusFilter
      const response = await laptopApi.getAll(params)
      const data = response.data
      if (data && Array.isArray(data.items)) {
        setLaptops(data.items)
        setTotal(typeof data.total === 'number' ? data.total : data.items.length)
        setInternWithoutLaptop(!!data.intern_without_laptop)
      } else {
        setLaptops(Array.isArray(data) ? data : [])
        setTotal(Array.isArray(data) ? data.length : 0)
        setInternWithoutLaptop(false)
      }
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(loadLaptops, 300)
    return () => clearTimeout(timer)
  }, [search, statusFilter])

  useEffect(() => subscribeDataChanged(loadLaptops), [loadLaptops])

  const resetForm = () => {
    setForm(emptyForm)
    setEditing(null)
    setFormError('')
  }

  const openAdd = () => {
    resetForm()
    setModalOpen(true)
  }

  const openEdit = (laptop) => {
    setEditing(laptop)
    setForm({
      laptop_number: laptop.laptop_number,
      brand: laptop.brand,
      model: laptop.model,
      serial_number: laptop.serial_number,
      status: laptop.status,
    })
    setFormError('')
    setModalOpen(true)
  }

  const handleFieldChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const validate = () => {
    if (!form.laptop_number.trim() || !form.brand.trim() || !form.model.trim() || !form.serial_number.trim()) {
      return 'All fields are required'
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9-_ ]*$/.test(form.laptop_number.trim())) {
      return 'Laptop Number can only contain letters, numbers, hyphens and underscores'
    }
    return ''
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setFormError(validationError)
      return
    }
    setSaving(true)
    setFormError('')
    try {
      const payload = {
        laptop_number: form.laptop_number.trim(),
        brand: form.brand.trim(),
        model: form.model.trim(),
        serial_number: form.serial_number.trim(),
        status: form.status,
      }
      if (editing) {
        const changes = {}
        Object.entries(payload).forEach(([k, v]) => {
          if (v !== editing[k]) changes[k] = v
        })
        if (Object.keys(changes).length > 0) {
          await laptopApi.update(editing.id, changes)
        }
        showToast('Laptop updated successfully')
      } else {
        await laptopApi.create(payload)
        showToast(`Laptop ${payload.laptop_number} added — available for allocation`)
      }
      setModalOpen(false)
      resetForm()
      notifyDataChanged()
      loadLaptops()
    } catch (err) {
      setFormError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (id, status) => {
    try {
      await laptopApi.updateStatus(id, status)
      showToast(`Status updated to ${status}`)
      notifyDataChanged()
      loadLaptops()
    } catch (err) {
      showToast(getErrorMessage(err), 'error')
    }
  }

  const handleActivateToggle = async (laptop) => {
    try {
      if (laptop.status === 'INACTIVE') {
        await laptopApi.activate(laptop.id)
        showToast('Laptop activated')
      } else {
        await laptopApi.deactivate(laptop.id)
        showToast('Laptop deactivated')
      }
      notifyDataChanged()
      loadLaptops()
    } catch (err) {
      showToast(getErrorMessage(err), 'error')
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Laptop Management"
        subtitle="Track and manage your laptop inventory"
        actions={
          <button onClick={openAdd} className="btn-primary">
            <Plus className="w-4 h-4" /> Add New Laptop
          </button>
        }
      />

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search laptop ID, intern ID, name, brand, batch..."
            className="input pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input sm:w-52"
        >
          <option value="">All Statuses</option>
          {FILTER_STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <ErrorBanner message={error} />

      <Card>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <LaptopIcon className="w-4 h-4 text-blue-600" />
            Laptops Inventory
          </div>
          <span className="text-sm text-slate-500">{total} laptop{total === 1 ? '' : 's'}</span>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : laptops.length === 0 ? (
          <div>
            <EmptyState
              title={
                search || statusFilter
                  ? internWithoutLaptop
                    ? 'No laptop currently allocated to this intern.'
                    : 'No laptops found'
                  : 'No laptop records imported yet.'
              }
              message={
                search || statusFilter
                  ? 'Try adjusting your search or filters'
                  : 'Import your Excel file to populate the laptop inventory.'
              }
            />
            {!search && !statusFilter && (
              <div className="px-5 pb-5">
                <ExcelImport />
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Laptop ID</th>
                  <th className="table-th">Intern ID</th>
                  <th className="table-th">Name</th>
                  <th className="table-th">Brand</th>
                  <th className="table-th">Batch</th>
                  <th className="table-th">Status</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {laptops.map((laptop) => (
                  <tr key={laptop.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{laptop.laptop_number}</td>
                    <td className="table-td text-slate-800">
                      {laptop.current_intern ? laptop.current_intern.intern_id : <span className="text-slate-400">—</span>}
                    </td>
                    <td className="table-td text-slate-800">
                      {laptop.current_intern ? laptop.current_intern.name : <span className="text-slate-400">—</span>}
                    </td>
                    <td className="table-td text-slate-700">{laptop.brand || '—'}</td>
                    <td className="table-td text-slate-700">
                      {laptop.current_intern && laptop.current_intern.batch
                        ? laptop.current_intern.batch
                        : <span className="text-slate-400">—</span>}
                    </td>
                    <td className="table-td"><StatusBadge status={laptop.status} /></td>
                    <td className="table-td">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setViewing(laptop)}
                          className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="View laptop details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openEdit(laptop)}
                          className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="Edit laptop"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <select
                          value={laptop.status}
                          onChange={(e) => handleStatusChange(laptop.id, e.target.value)}
                          className="text-xs border border-slate-300 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                          title="Change status"
                        >
                          {FILTER_STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleActivateToggle(laptop)}
                          className={`p-2 rounded-lg transition-colors ${
                            laptop.status === 'INACTIVE'
                              ? 'text-emerald-600 hover:bg-emerald-50'
                              : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                          }`}
                          title={laptop.status === 'INACTIVE' ? 'Activate laptop' : 'Deactivate laptop'}
                        >
                          <Power className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Edit Laptop' : 'Add New Laptop'}
        icon={<LaptopIcon className="w-5 h-5" />}
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button
              type="submit"
              form="laptop-form"
              disabled={saving}
              className="btn-primary"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? 'Saving...' : editing ? 'Update Laptop' : 'Add Laptop'}
            </button>
          </>
        }
      >
        <form id="laptop-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="laptop_number" className="label">Laptop Number *</label>
              <input
                id="laptop_number"
                name="laptop_number"
                value={form.laptop_number}
                onChange={handleFieldChange}
                placeholder="e.g. LP-021"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="brand" className="label">Brand *</label>
              <input
                id="brand"
                name="brand"
                value={form.brand}
                onChange={handleFieldChange}
                placeholder="e.g. Dell"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="model" className="label">Model *</label>
              <input
                id="model"
                name="model"
                value={form.model}
                onChange={handleFieldChange}
                placeholder="e.g. Latitude 5520"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="serial_number" className="label">Serial Number *</label>
              <input
                id="serial_number"
                name="serial_number"
                value={form.serial_number}
                onChange={handleFieldChange}
                placeholder="e.g. SN-021"
                className="input"
              />
            </div>
          </div>

          <div>
            <label htmlFor="status" className="label">Status</label>
            <select id="status" name="status" value={form.status} onChange={handleFieldChange} className="input">
              {FORM_STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-slate-400 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" />
              {editing ? 'Status can also be changed later from the list.' : 'New laptops are marked Free and become immediately available for allocation.'}
            </p>
          </div>

          {formError && <ErrorBanner message={formError} />}
        </form>
      </Modal>

      <Modal
        open={!!viewing}
        onClose={() => setViewing(null)}
        title={viewing ? `Laptop ${viewing.laptop_number}` : 'Laptop Details'}
        icon={<LaptopIcon className="w-5 h-5" />}
        footer={
          <button type="button" onClick={() => setViewing(null)} className="btn-secondary">Close</button>
        }
      >
        {viewing && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <DetailItem label="Laptop ID" value={viewing.laptop_number} />
              <DetailItem label="Brand" value={viewing.brand || '—'} />
              <DetailItem label="Model" value={viewing.model || '—'} />
              <DetailItem label="Status" value={<StatusBadge status={viewing.status} />} />
              {viewing.current_intern && viewing.current_intern.batch && (
                <DetailItem label="Batch" value={viewing.current_intern.batch} />
              )}
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Current Allocation</p>
              {viewing.current_intern ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <DetailItem label="Intern ID" value={viewing.current_intern.intern_id} />
                  <DetailItem label="Name" value={viewing.current_intern.name} />
                  <DetailItem label="Email" value={viewing.current_intern.email} />
                  <DetailItem label="Domain" value={viewing.current_intern.domain || '—'} />
                </div>
              ) : (
                <p className="text-sm text-slate-500">Not allocated — this laptop is currently unassigned.</p>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function DetailItem({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-medium text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-slate-800">{value}</dd>
    </div>
  )
}

export default Laptops