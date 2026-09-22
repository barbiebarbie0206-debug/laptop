import { useEffect, useState } from 'react'
import { ArrowLeftRight, User, Laptop, Calendar, Clock, Loader2, Info, Sun, Sunset, SunMoon, Users, Search } from 'lucide-react'
import { allocationApi, internApi, getErrorMessage } from '../services/api'
import { useToast } from '../components/Toast'
import { notifyDataChanged } from '../services/events'
import { PageHeader, BatchBadge, StatCard } from '../components/ui'
import { Card, ErrorBanner } from '../components/StateComponents'

function timeToMinutes(t) {
  const [h, m] = String(t).split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}

function AllocateLaptop() {
  const showToast = useToast()
  const [interns, setInterns] = useState([])
  const [availableLaptops, setAvailableLaptops] = useState([])
  const [batchSummary, setBatchSummary] = useState({ morning: 0, afternoon: 0, full_day: 0, total: 0 })
  const [internQuery, setInternQuery] = useState('')
  const [showInternResults, setShowInternResults] = useState(false)
  const [selectedIntern, setSelectedIntern] = useState(null)
  const [selectedLaptopId, setSelectedLaptopId] = useState('')
  const [allocationDate, setAllocationDate] = useState(() => new Date().toISOString().split('T')[0])
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('12:00')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadData = async (refreshLaptops = false) => {
    try {
      const [internsRes, laptopsRes, summaryRes] = await Promise.all([
        allocationApi.getAllocatableInterns(),
        refreshLaptops ? allocationApi.getAvailableLaptops() : Promise.resolve(null),
        internApi.getBatchSummary(),
      ])
      setInterns(Array.isArray(internsRes.data) ? internsRes.data : [])
      if (refreshLaptops) {
        setAvailableLaptops(Array.isArray(laptopsRes.data) ? laptopsRes.data : [])
      }
      if (summaryRes && summaryRes.data) {
        setBatchSummary(summaryRes.data)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData(true)
  }, [])

  const selectIntern = (intern) => {
    setSelectedIntern(intern)
    setInternQuery(intern.intern_id)
    setShowInternResults(false)
    setError('')
  }

  const handleInternQueryChange = (value) => {
    setInternQuery(value)
    setSelectedIntern(null)
    setShowInternResults(true)
    setError('')
  }

  const internQueryTrimmed = internQuery.trim().toLowerCase()
  const exactIntern = internQueryTrimmed
    ? interns.find((i) => i.intern_id.trim().toLowerCase() === internQueryTrimmed) || null
    : null
  const searchResults = internQueryTrimmed
    ? [
        ...(exactIntern ? [exactIntern] : []),
        ...interns.filter(
          (i) =>
            i !== exactIntern &&
            (i.intern_id.trim().toLowerCase().startsWith(internQueryTrimmed) ||
              (i.name || '').toLowerCase().includes(internQueryTrimmed))
        ),
      ].slice(0, 8)
    : []
  const internNotFound = internQueryTrimmed !== '' && searchResults.length === 0

  useEffect(() => {
    const query = internQuery.trim().toLowerCase()
    if (!query) return
    const exact = interns.find((i) => i.intern_id.trim().toLowerCase() === query)
    const matches = exact
      ? [exact]
      : interns.filter(
          (i) =>
            i.intern_id.trim().toLowerCase().startsWith(query) ||
            (i.name || '').toLowerCase().includes(query)
        )
    if (matches.length === 1) {
      selectIntern(matches[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [internQuery, interns])

  const allocatable = interns.filter((i) => !i.has_active_allocation)
  const batchGroups = [
    { key: 'Morning', label: 'Morning Batch' },
    { key: 'Afternoon', label: 'Afternoon Batch' },
    { key: 'Full Day', label: 'Full Day' },
  ].map((group) => {
    const members = allocatable.filter((i) => i.batch === group.key)
    return { ...group, members, count: members.length }
  })
  const totalAllocatable = batchGroups.reduce((sum, g) => sum + g.count, 0)
  const timeInvalid = startTime && endTime && timeToMinutes(endTime) <= timeToMinutes(startTime)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedIntern) {
      setError('Select a valid intern by its Intern ID.')
      return
    }
    if (!selectedLaptopId) return
    if (timeInvalid) {
      setError('End time must be after start time')
      return
    }
    if (selectedIntern.has_active_allocation) {
      setError(`${selectedIntern.intern_id} already has an active laptop allocation.`)
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await allocationApi.create({
        laptop_id: Number(selectedLaptopId),
        intern_id: selectedIntern.id,
        allocation_date: allocationDate,
        start_time: startTime,
        end_time: endTime,
      })
      const laptop = availableLaptops.find((l) => l.id === Number(selectedLaptopId))
      showToast(`${laptop?.laptop_number || 'Laptop'} allocated to ${selectedIntern.name}`)
      notifyDataChanged()
      setSelectedLaptopId('')
      setInternQuery('')
      setSelectedIntern(null)
      loadData(true)
    } catch (err) {
      setError(getErrorMessage(err))
      loadData(true)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Allocate Laptop"
        subtitle="Select an intern and assign an available laptop"
      />

      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Sun className="w-5 h-5" />}
          label="Morning Batch"
          value={batchSummary.morning}
          iconClass="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon={<Sunset className="w-5 h-5" />}
          label="Afternoon Batch"
          value={batchSummary.afternoon}
          iconClass="bg-orange-50 text-orange-600"
        />
        <StatCard
          icon={<SunMoon className="w-5 h-5" />}
          label="Full Day"
          value={batchSummary.full_day}
          iconClass="bg-violet-50 text-violet-600"
        />
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="Total Interns"
          value={batchSummary.total}
          iconClass="bg-slate-100 text-slate-600"
        />
      </div>

      <Card className="overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-3">
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-50 text-blue-600">
            <ArrowLeftRight className="w-5 h-5" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">New Allocation</h2>
            <p className="text-xs text-slate-400">Issue a laptop for a time slot</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label htmlFor="intern" className="label flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5" /> Select / Enter Intern ID *
                </label>
                <div className="relative">
                  <input
                    id="intern"
                    type="text"
                    value={internQuery}
                    onChange={(e) => handleInternQueryChange(e.target.value)}
                    onFocus={() => setShowInternResults(true)}
                    onBlur={() => setTimeout(() => setShowInternResults(false), 150)}
                    placeholder="Enter Intern ID (e.g. INT001)"
                    autoComplete="off"
                    spellCheck={false}
                    className="input pr-10"
                  />
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />

                  {showInternResults && internQuery.trim() !== '' && searchResults.length > 0 && (
                    <div className="absolute z-20 mt-1 w-full max-h-72 overflow-y-auto rounded-xl bg-white border border-slate-200 shadow-popover py-1">
                      {exactIntern && (
                        <p className="px-3 pt-1.5 pb-1 text-[11px] font-semibold text-emerald-600 uppercase tracking-wide">
                          Exact match
                        </p>
                      )}
                      {searchResults.map((intern) => (
                        <button
                          key={intern.id}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault()
                            selectIntern(intern)
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center justify-between gap-2"
                        >
                          <span className="text-sm min-w-0 truncate">
                            <span className="font-semibold text-slate-800">{intern.intern_id}</span>
                            <span className="text-slate-400 mx-1">-</span>
                            <span className="text-slate-700">{intern.name}</span>
                          </span>
                          <span className="inline-flex items-center gap-2 shrink-0">
                            <BatchBadge batch={intern.batch} />
                            {intern.has_active_allocation && (
                              <span className="text-[11px] font-medium text-amber-600">Busy</span>
                            )}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {showInternResults && internNotFound && (
                    <div className="absolute z-20 mt-1 w-full rounded-xl bg-white border border-red-200 shadow-popover px-3 py-2.5 text-sm text-red-600">
                      Intern ID not found
                    </div>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                  {batchGroups.map((group) => (
                    <span key={group.key}>
                      <span className="font-medium text-slate-700">{group.label.replace(' Batch', '')}:</span>{' '}
                      {group.count}
                    </span>
                  ))}
                  <span>
                    <span className="font-medium text-slate-700">Total:</span> {totalAllocatable}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-slate-400">
                  {totalAllocatable} intern{totalAllocatable === 1 ? '' : 's'} available (without an active allocation)
                </p>
              </div>

              {selectedIntern && (
                <div className={`rounded-xl border p-4 ${selectedIntern.has_active_allocation ? 'border-amber-200 bg-amber-50/60' : 'border-blue-100 bg-blue-50/60'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wide mb-3 ${selectedIntern.has_active_allocation ? 'text-amber-700' : 'text-blue-700'}`}>Intern Details</p>
                  {selectedIntern.has_active_allocation && (
                    <p className="mb-3 text-xs font-medium text-amber-700">
                      This intern already has an active laptop allocation and cannot be allocated again.
                    </p>
                  )}
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                    <div>
                      <dt className="text-xs text-slate-500">Intern ID</dt>
                      <dd className="font-medium text-slate-800">{selectedIntern.intern_id}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Name</dt>
                      <dd className="font-medium text-slate-800">{selectedIntern.name}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Email</dt>
                      <dd className="font-medium text-slate-800 truncate">{selectedIntern.email}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Phone</dt>
                      <dd className="font-medium text-slate-800">{selectedIntern.phone}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Batch</dt>
                      <dd className="pt-0.5"><BatchBadge batch={selectedIntern.batch} /></dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Domain</dt>
                      <dd className="font-medium text-slate-800">{selectedIntern.domain}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="laptop" className="label flex items-center gap-1.5">
                  <Laptop className="w-3.5 h-3.5" /> Available Laptops *
                </label>
                {loading ? (
                  <div className="flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-400">
                    <Loader2 className="w-4 h-4 animate-spin" /> Loading available laptops...
                  </div>
                ) : (
                  <select
                    id="laptop"
                    value={selectedLaptopId}
                    onChange={(e) => setSelectedLaptopId(e.target.value)}
                    className="input"
                  >
                    <option value="">-- Choose a laptop --</option>
                    {availableLaptops.map((laptop) => (
                      <option key={laptop.id} value={laptop.id}>
                        {laptop.laptop_number} — {laptop.brand} {laptop.model}
                      </option>
                    ))}
                  </select>
                )}
                <p className="mt-1.5 text-xs text-slate-400 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" />
                  {availableLaptops.length} free laptop{availableLaptops.length === 1 ? '' : 's'} available right now
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="allocation_date" className="label flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5" /> Date *
                  </label>
                  <input
                    id="allocation_date"
                    type="date"
                    value={allocationDate}
                    onChange={(e) => setAllocationDate(e.target.value)}
                    required
                    className="input"
                  />
                </div>
                <div>
                  <label htmlFor="start_time" className="label flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" /> Start *
                  </label>
                  <input
                    id="start_time"
                    type="time"
                    value={startTime}
                    onChange={(e) => { setStartTime(e.target.value); setError('') }}
                    required
                    className="input"
                  />
                </div>
                <div>
                  <label htmlFor="end_time" className="label flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" /> End *
                  </label>
                  <input
                    id="end_time"
                    type="time"
                    value={endTime}
                    onChange={(e) => { setEndTime(e.target.value); setError('') }}
                    required
                    className={`input ${timeInvalid ? 'input-invalid' : ''}`}
                  />
                </div>
              </div>
              {timeInvalid && (
                <p className="text-xs text-red-600">End time must be after start time.</p>
              )}

              <button
                type="submit"
                disabled={
                submitting ||
                !selectedIntern ||
                selectedIntern.has_active_allocation ||
                !selectedLaptopId
              }
                className="btn-primary w-full py-2.5"
              >
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {submitting ? 'Allocating...' : 'Allocate Laptop'}
              </button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  )
}

export default AllocateLaptop