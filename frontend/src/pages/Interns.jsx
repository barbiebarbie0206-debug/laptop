import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Search, Edit2, Trash2, Users as UsersIcon, Loader2, Info } from 'lucide-react'
import { internApi, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import { notifyDataChanged } from '../services/events'
import ConfirmDialog from '../components/ConfirmDialog'
import { BATCH_OPTIONS, DOMAIN_OPTIONS } from '../constants'
import { PageHeader, Modal, BatchBadge } from '../components/ui'
import { Card, LoadingSpinner, EmptyState, ErrorBanner } from '../components/StateComponents'

const emptyForm = {
  intern_id: '',
  name: '',
  email: '',
  phone: '',
  batch: 'Morning',
  domain: 'Cloud',
}

function Interns() {
  const navigate = useNavigate()
  const location = useLocation()
  const showToast = useToast()

  const initialQuery = new URLSearchParams(location.search).get('q') || ''

  const [interns, setInterns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState(initialQuery)
  const [batchFilter, setBatchFilter] = useState('')
  const [domainFilter, setDomainFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (new URLSearchParams(location.search).get('add') === '1') {
      setModalOpen(true)
      const qs = initialQuery ? `?q=${encodeURIComponent(initialQuery)}` : ''
      navigate(location.pathname + qs, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadInterns = async () => {
    try {
      setLoading(true)
      const params = {}
      if (search.trim()) params.search = search.trim()
      if (batchFilter) params.batch = batchFilter
      if (domainFilter) params.domain = domainFilter
      const response = await internApi.getAll(params)
      setInterns(Array.isArray(response.data) ? response.data : [])
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(loadInterns, 300)
    return () => clearTimeout(timer)
  }, [search, batchFilter, domainFilter])

  const resetForm = () => {
    setForm(emptyForm)
    setEditing(null)
    setFormError('')
  }

  const openAdd = () => {
    resetForm()
    setModalOpen(true)
  }

  const openEdit = (intern) => {
    setEditing(intern)
    setForm({
      intern_id: intern.intern_id,
      name: intern.name,
      email: intern.email,
      phone: intern.phone,
      batch: intern.batch,
      domain: intern.domain,
    })
    setFormError('')
    setModalOpen(true)
  }

  const handleFieldChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const validate = () => {
    if (!form.intern_id.trim() || !form.name.trim() || !form.email.trim() || !form.phone.trim()) {
      return 'All fields are required'
    }
    if (!/^[\w-]+$/.test(form.intern_id.trim())) {
      return 'Intern ID can only contain letters, numbers, hyphens and underscores'
    }
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
      return 'Enter a valid email address'
    }
    if (!/^[0-9+()\-.\s]{7,}$/.test(form.phone.trim())) {
      return 'Enter a valid phone number'
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
        intern_id: form.intern_id.trim(),
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        batch: form.batch,
        domain: form.domain,
      }
      if (editing) {
        const changes = {}
        Object.entries(payload).forEach(([k, v]) => {
          if (v !== editing[k]) changes[k] = v
        })
        if (Object.keys(changes).length > 0) {
          await internApi.update(editing.id, changes)
        }
        showToast('Intern updated successfully')
      } else {
        await internApi.create(payload)
        showToast('Intern added successfully')
      }
      notifyDataChanged()
      setModalOpen(false)
      resetForm()
      loadInterns()
    } catch (err) {
      setFormError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await internApi.delete(deleteTarget.id)
      showToast('Intern deleted successfully')
      notifyDataChanged()
      setDeleteTarget(null)
      loadInterns()
    } catch (err) {
      showToast(getErrorMessage(err), 'error')
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Intern Management"
        subtitle="Register and manage intern records"
        actions={
          <button onClick={openAdd} className="btn-primary">
            <Plus className="w-4 h-4" /> Add New Intern
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
            placeholder="Search by intern ID, name, email or phone..."
            className="input pl-9"
          />
        </div>
        <select value={batchFilter} onChange={(e) => setBatchFilter(e.target.value)} className="input sm:w-44">
          <option value="">All Batches</option>
          {BATCH_OPTIONS.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} className="input sm:w-52">
          <option value="">All Domains</option>
          {DOMAIN_OPTIONS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      <ErrorBanner message={error} />

      <Card>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <UsersIcon className="w-4 h-4 text-blue-600" />
            Intern Records
          </div>
          <span className="text-sm text-slate-500">{interns.length} intern{interns.length === 1 ? '' : 's'}</span>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : interns.length === 0 ? (
          <EmptyState
            title="No interns found"
            message={search || batchFilter || domainFilter ? 'Try adjusting your search or filters' : 'Click “Add New Intern” to register your first intern'}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Intern ID</th>
                  <th className="table-th">Name</th>
                  <th className="table-th">Email</th>
                  <th className="table-th">Phone</th>
                  <th className="table-th">Batch</th>
                  <th className="table-th">Domain</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {interns.map((intern) => (
                  <tr key={intern.id} className="hover:bg-slate-50">
                    <td className="table-td font-semibold text-slate-800">{intern.intern_id}</td>
                    <td className="table-td text-slate-800">
                      <span className="flex items-center gap-2.5">
                        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-50 text-blue-700 text-[11px] font-bold shrink-0">
                          {String(intern.name).split(' ').filter(Boolean).map((p) => p[0]).slice(0, 2).join('').toUpperCase()}
                        </span>
                        {intern.name}
                      </span>
                    </td>
                    <td className="table-td">{intern.email}</td>
                    <td className="table-td">{intern.phone}</td>
                    <td className="table-td"><BatchBadge batch={intern.batch} /></td>
                    <td className="table-td">{intern.domain}</td>
                    <td className="table-td">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openEdit(intern)}
                          className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="Edit intern"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(intern)}
                          className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                          title="Delete intern"
                        >
                          <Trash2 className="w-4 h-4" />
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
        title={editing ? 'Edit Intern' : 'Add New Intern'}
        icon={<UsersIcon className="w-5 h-5" />}
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button
              type="submit"
              form="intern-form"
              disabled={saving}
              className="btn-primary"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? 'Saving...' : editing ? 'Update Intern' : 'Add Intern'}
            </button>
          </>
        }
      >
        <form id="intern-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="intern_id" className="label">Intern ID *</label>
              <input
                id="intern_id"
                name="intern_id"
                value={form.intern_id}
                onChange={handleFieldChange}
                placeholder="e.g. INT-011"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="name" className="label">Full Name *</label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={handleFieldChange}
                placeholder="Full name"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="email" className="label">Email *</label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleFieldChange}
                placeholder="intern@example.com"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="phone" className="label">Phone *</label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={form.phone}
                onChange={handleFieldChange}
                placeholder="Phone number"
                className="input"
              />
            </div>
            <div>
              <label htmlFor="batch" className="label">Batch *</label>
              <select id="batch" name="batch" value={form.batch} onChange={handleFieldChange} className="input">
                {BATCH_OPTIONS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="domain" className="label">Domain *</label>
              <select id="domain" name="domain" value={form.domain} onChange={handleFieldChange} className="input">
                {DOMAIN_OPTIONS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <p className="text-xs text-slate-400 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" />
            Batch and domain can be changed any time; interns without an active allocation are allocatable.
          </p>

          {formError && <ErrorBanner message={formError} />}
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Intern"
        message={
          deleteTarget
            ? `Are you sure you want to permanently delete ${deleteTarget.name} (${deleteTarget.intern_id})? This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        danger
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

export default Interns