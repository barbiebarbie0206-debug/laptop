import { useCallback, useRef, useState } from 'react'
import {
  FileSpreadsheet,
  UploadCloud,
  X,
  Download,
  FileDown,
  AlertTriangle,
  Loader2,
  Ban,
  CheckCircle2,
  FileCheck2,
} from 'lucide-react'
import { excelApi, getErrorMessage } from '../services/api'
import { notifyDataChanged } from '../services/events'
import { downloadBlob } from './StateComponents'
import { useToast } from './Toast'

const MAX_SIZE = 10 * 1024 * 1024

const REQUIRED_COLUMNS = [
  'Laptop ID',
  'Laptop Name',
  'Brand',
  'Model',
  'Serial Number',
  'RAM',
  'Storage',
  'Intern ID',
  'Intern Name',
  'Email',
  'Domain',
  'Allocation Date',
  'Return Date',
  'Status',
]

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function isExcelFile(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  return ext === 'xlsx' || ext === 'xls'
}

function ExcelImport() {
  const toast = useToast()
  const inputRef = useRef(null)
  const controllerRef = useRef(null)

  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [phase, setPhase] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [busyAction, setBusyAction] = useState('')

  const acceptFile = useCallback(
    (candidate) => {
      if (phase === 'uploading') return
      if (!candidate) return
      if (!isExcelFile(candidate)) {
        toast('Invalid file format. Please upload a .xlsx or .xls Excel file.', 'error')
        return
      }
      if (candidate.size > MAX_SIZE) {
        toast('Excel file exceeds the maximum allowed size (10 MB).', 'error')
        return
      }
      setFile(candidate)
      setResult(null)
      setProgress(0)
    },
    [phase, toast]
  )

  const onDrop = useCallback(
    (e) => {
      e.preventDefault()
      setDragging(false)
      acceptFile(e.dataTransfer.files[0])
    },
    [acceptFile]
  )

  const openPicker = () => {
    if (inputRef.current) inputRef.current.click()
  }

  const handleImport = async () => {
    if (!file || phase === 'uploading') return
    setResult(null)
    setPhase('uploading')
    setProgress(0)
    controllerRef.current = new AbortController()
    try {
      const res = await excelApi.importExcel(file, setProgress, controllerRef.current.signal)
      const data = res.data
      setResult(data)
      notifyDataChanged()
      toast(
        data.success
          ? data.message || `Excel imported successfully — ${data.inserted} added, ${data.updated} updated`
          : data.message || 'No records were imported. Please review the errors.',
        data.success ? 'success' : 'error'
      )
    } catch (err) {
      const canceled = err && err.code === 'ERR_CANCELED'
      if (!canceled) toast(getErrorMessage(err), 'error')
    } finally {
      setPhase('idle')
      controllerRef.current = null
    }
  }

  const handleCancel = () => {
    if (controllerRef.current) controllerRef.current.abort()
    setPhase('idle')
    setProgress(0)
  }

  const handleTemplate = async () => {
    setBusyAction('template')
    try {
      const res = await excelApi.downloadTemplate()
      downloadBlob(res.data, 'laptop_import_template.xlsx')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const handleExport = async () => {
    setBusyAction('export')
    try {
      const res = await excelApi.exportExcel()
      downloadBlob(res.data, 'laptop_allocations_export.xlsx')
    } catch (err) {
      toast(getErrorMessage(err), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const uploading = phase === 'uploading'
  const summaryChips = result
    ? [
        { label: 'Excel Rows Read', value: result.rows_read ?? result.total_rows, cls: 'bg-slate-100 text-slate-700' },
        { label: 'Sheets Read', value: result.sheets_read ?? '—', cls: 'bg-slate-100 text-slate-700' },
        { label: 'Laptops Added', value: result.inserted, cls: 'bg-emerald-50 text-emerald-700' },
        { label: 'Laptops Updated', value: result.updated, cls: 'bg-blue-50 text-blue-700' },
        { label: 'Duplicates Skipped', value: result.duplicates, cls: 'bg-amber-50 text-amber-700' },
        { label: 'Invalid Rows', value: result.invalid, cls: 'bg-red-50 text-red-700' },
        {
          label: 'Total Laptops in DB',
          value: result.laptops_total,
          cls: 'bg-indigo-50 text-indigo-700',
        },
      ]
    : []

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-5 py-4 border-b border-slate-200 bg-slate-50/60">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100 shrink-0">
            <FileSpreadsheet className="w-6 h-6" />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Excel Import / Export</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Bulk import laptops, interns and allocations from a spreadsheet
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            onClick={handleTemplate}
            disabled={uploading || busyAction === 'template'}
            className="btn-secondary"
          >
            {busyAction === 'template' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Download Template
          </button>
          <button
            onClick={handleExport}
            disabled={uploading || busyAction === 'export'}
            className="btn-secondary"
          >
            {busyAction === 'export' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            Export Excel
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 p-5">
        {/* Upload area */}
        <div className="lg:col-span-3 space-y-4">
          {!file ? (
            <div
              onDragOver={(e) => {
                e.preventDefault()
                if (!uploading) setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl px-6 py-12 text-center transition-colors ${
                dragging
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-slate-300 bg-slate-50 hover:border-blue-300 hover:bg-blue-50/40'
              }`}
            >
              <span className="flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-100 text-blue-600">
                <UploadCloud className="w-8 h-8" />
              </span>
              <div>
                <p className="text-sm font-medium text-slate-800">Drag &amp; drop your Excel file here</p>
                <p className="text-xs text-slate-400 mt-1">or</p>
              </div>
              <button type="button" onClick={openPicker} className="btn-primary">
                <UploadCloud className="w-4 h-4" /> Choose File
              </button>
              <p className="text-xs text-slate-400">Supported: .xlsx / .xls · Maximum size: 10 MB</p>
              <input
                ref={inputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                disabled={uploading}
                onChange={(e) => {
                  acceptFile(e.target.files[0])
                  e.target.value = ''
                }}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50">
                <span className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 shrink-0">
                  <FileSpreadsheet className="w-5 h-5" />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
                  <p className="text-xs text-slate-400">{formatBytes(file.size)}</p>
                  {uploading && (
                    <div className="mt-2 h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-500 transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  )}
                </div>
                {!uploading && (
                  <button
                    onClick={() => {
                      setFile(null)
                      setResult(null)
                    }}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    title="Clear file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {uploading ? (
                  <button onClick={handleCancel} className="btn-danger-soft">
                    <Ban className="w-4 h-4" />
                    Cancel Import
                  </button>
                ) : (
                  <>
                    <button onClick={handleImport} className="btn-primary">
                      <UploadCloud className="w-4 h-4" />
                      Import Excel
                    </button>
                    <button
                      onClick={() => {
                        setFile(null)
                        setResult(null)
                      }}
                      className="btn-secondary"
                    >
                      <X className="w-4 h-4" />
                      Clear
                    </button>
                  </>
                )}
              </div>

              {uploading && (
                <p className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Uploading and processing file… {progress}%
                </p>
              )}
            </div>
          )}

          {/* Result summary */}
          {result && (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
              <div
                className={`flex items-center gap-2 px-4 py-3 border-b border-slate-200 ${
                  result.success ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                }`}
              >
                {result.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <p className="text-sm font-semibold">
                  {result.success ? 'Excel Import Successful' : 'Nothing was imported'}
                </p>
              </div>
              <div className="px-4 py-4">
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {summaryChips.map((chip) => (
                    <div key={chip.label} className={`flex flex-col items-center gap-1 rounded-lg px-3 py-3 ${chip.cls}`}>
                      <span className="text-xl font-bold leading-none">{chip.value}</span>
                      <span className="text-xs font-medium text-center leading-tight">{chip.label}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-sm text-slate-600">{result.message}</p>
                {result.errors && result.errors.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                      Invalid rows ({result.errors.length})
                    </p>
                    <ul className="max-h-40 overflow-y-auto space-y-1.5">
                      {result.errors.map((err, idx) => (
                        <li
                          key={`${err.row}-${idx}`}
                          className="flex items-start gap-2 text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2"
                        >
                          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                          <span>
                            <span className="font-semibold">Row {err.row}:</span> {err.error}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Required columns */}
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5">
            <div className="flex items-center gap-2 mb-1">
              <FileCheck2 className="w-4 h-4 text-blue-600" />
              <h4 className="text-sm font-semibold text-slate-900">Required Excel Columns</h4>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              The importer reads every worksheet in the workbook and merges records by Laptop ID.
              Your spreadsheet must contain these columns (common aliases such as Asset, Name,
              Model No, Serial are also accepted).
            </p>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2">
              {REQUIRED_COLUMNS.map((col) => (
                <li key={col} className="flex items-center gap-2 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  {col}
                </li>
              ))}
            </ul>
            <div className="mt-4 pt-4 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Valid Domains</p>
              <div className="flex flex-wrap gap-1.5">
                {['Cloud', 'Data Analytics', 'Full Stack', 'AI & ML', 'Digital Marketing', 'UI/UX'].map((d) => (
                  <span key={d} className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[11px] font-medium ring-1 ring-blue-100">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExcelImport