"""Excel import / export endpoints for the Laptop Allocation Management System.

Import flow:   POST /api/v1/import/excel      (multipart .xlsx / .xls upload)
Export flow:   GET  /api/v1/export/excel      (current records as a .xlsx report)
Template flow: GET  /api/v1/export/template   (downloadable import template)

Reading/hydration uses the low-level openpyxl / xlrd readers and reads every
worksheet in the workbook (not just the first). Sheets are processed in a
priority order and merged per unique Laptop ID, so a laptop appearing in
multiple sheets is imported exactly once with the most complete attributes.

The importer accepts the canonical template headers plus a set of common
aliases so real-world sheets (e.g. "Asset", "Model No", "Time Shift", "#No"
counter columns) can be imported directly. Rows are validated individually,
persisted through SQLite SAVEPOINTs so a bad row is skipped without rolling back
the whole file, and the transaction is committed once at the end.
"""
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from io import BytesIO
from os import path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.allocation import Allocation, AllocationStatus
from ..models.intern import Batch, Domain, Intern
from ..models.laptop import Laptop, LaptopStatus
from ..models.user import User

logger = logging.getLogger("laptop_allocation.excel_io")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = (".xlsx", ".xls")

EXPORT_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

DOMAIN_OPTIONS = [
    "Cloud",
    "Data Analytics",
    "Full Stack",
    "AI & ML",
    "Digital Marketing",
    "UI/UX",
]
STATUS_OPTIONS = [
    LaptopStatus.FREE.value,
    LaptopStatus.ALLOCATED.value,
    LaptopStatus.MAINTENANCE.value,
    LaptopStatus.INACTIVE.value,
]

DATE_FORMAT = "yyyy-mm-dd"


class ImportRowError(BaseModel):
    row: int
    error: str


class ImportSummary(BaseModel):
    success: bool
    message: str
    total_rows: int
    inserted: int
    updated: int
    duplicates: int
    invalid: int
    skipped: int  # backwards-compatible alias for duplicates + invalid
    errors: List[ImportRowError]
    rows_read: int = 0  # raw data rows read across all worksheets
    sheets_read: int = 0  # number of worksheets processed
    laptops_total: int = 0  # final laptop count in the database after import
    interns_total: int = 0  # final intern count in the database after import


class ImportRow:
    """Mutable bookkeeping for a single Excel row while it is being processed."""

    def __init__(self) -> None:
        self.inserted = False
        self.updated = False


# ---------------------------------------------------------------------------
# Column mapping: canonical field -> ordered list of accepted header names.
# The first name in each list is the canonical template header.
# ---------------------------------------------------------------------------
COLUMN_MAP: Dict[str, List[str]] = {
    "asset_tag": [
        "Laptop ID", "Laptop Name", "Asset Tag", "Asset", "Laptop Code",
        "Asset ID", "Asset Number", "Asset No", "Laptop Number",
        "Model No", "Model Number", "Tag No", "Tag", "Serial", "Serial No",
    ],
    "brand": ["Brand", "Make", "Manufacturer"],
    "model": ["Model", "Model Name", "Laptop Model"],
    "serial_number": ["Serial Number", "Serial", "SN", "Service Tag"],
    "processor": ["Processor", "CPU"],
    "ram": ["RAM", "Memory"],
    "storage": ["Storage", "Hard Drive", "HDD", "SSD", "Disk"],
    "operating_system": ["Operating System", "OS", "Platform"],
    "status": ["Status", "IT Support"],
    "intern_id": ["Intern ID", "Employee ID", "Emp ID", "Student ID", "Intern Code"],
    "intern_name": ["Intern Name", "Name", "Student Name", "Employee Name", "User Name", "Full Name"],
    "email": ["Email", "Email ID", "E-mail", "Email Address"],
    "phone": ["Phone", "Mobile", "Phone Number", "Mobile Number"],
    "department": ["Department", "Dept", "Department Name"],
    "domain": ["Domain", "Stream", "Specialization"],
    "batch": ["Batch", "Shift Name", "Session"],
    "allocation_date": ["Allocation Date", "Allocated Date", "Date of Allocation", "Assign Date"],
    "return_date": ["Return Date", "Returned Date", "Date of Return"],
    "time_shift": ["Time Shift", "Shift Timing", "Timing", "Session Time"],
}

TEMPLATE_HEADERS = [
    "Laptop ID", "Laptop Name", "Brand", "Model", "Serial Number",
    "RAM", "Storage", "Intern ID", "Intern Name", "Email", "Domain",
    "Allocation Date", "Return Date", "Status",
]

TEMPLATE_SAMPLE = [
    "LP-101", "ASSET-101", "Dell", "Latitude 5520", "SN-101",
    "8 GB", "256 GB SSD", "INT-101", "John Doe", "john.doe@example.com",
    "Cloud", datetime(2026, 9, 8), datetime(2026, 10, 8), LaptopStatus.FREE.value,
]

TEMPLATE_WIDTHS = {
    "A": 13, "B": 16, "C": 12, "D": 20, "E": 16,
    "F": 10, "G": 14, "H": 12, "I": 20, "J": 28,
    "K": 18, "L": 15, "M": 15, "N": 16,
}

STATUS_NORMALIZE: Dict[str, LaptopStatus] = {
    "free": LaptopStatus.FREE,
    "available": LaptopStatus.FREE,
    "in hand": LaptopStatus.FREE,
    "inhand": LaptopStatus.FREE,
    "in stock": LaptopStatus.FREE,
    "stock": LaptopStatus.FREE,
    "allocated": LaptopStatus.ALLOCATED,
    "hand over": LaptopStatus.ALLOCATED,
    "handover": LaptopStatus.ALLOCATED,
    "issued": LaptopStatus.ALLOCATED,
    "in use": LaptopStatus.ALLOCATED,
    "in progress": LaptopStatus.ALLOCATED,
    "inprogress": LaptopStatus.ALLOCATED,
    "maintenance": LaptopStatus.MAINTENANCE,
    "repair": LaptopStatus.MAINTENANCE,
    "service": LaptopStatus.MAINTENANCE,
    "inactive": LaptopStatus.INACTIVE,
    "retired": LaptopStatus.INACTIVE,
    "disposed": LaptopStatus.INACTIVE,
}

BATCH_ALIASES: Dict[str, Batch] = {
    "morning": Batch.MORNING,
    "am": Batch.MORNING,
    "afternoon": Batch.AFTERNOON,
    "pm": Batch.AFTERNOON,
    "evening": Batch.AFTERNOON,
    "full day": Batch.FULL_DAY,
    "full-day": Batch.FULL_DAY,
    "fullday": Batch.FULL_DAY,
    "whole day": Batch.FULL_DAY,
    "general": Batch.FULL_DAY,
}

DOMAIN_ALIASES: Dict[str, Domain] = {
    "cloud": Domain.CLOUD,
    "data analytics": Domain.DATA_ANALYTICS,
    "dataanalysis": Domain.DATA_ANALYTICS,
    "analytics": Domain.DATA_ANALYTICS,
    "data analyst": Domain.DATA_ANALYTICS,
    "full stack": Domain.FULL_STACK,
    "fullstack": Domain.FULL_STACK,
    "ai & ml": Domain.AI_ML,
    "ai and ml": Domain.AI_ML,
    "ai&ml": Domain.AI_ML,
    "ai/ml": Domain.AI_ML,
    "ai ml": Domain.AI_ML,
    "aiml": Domain.AI_ML,
    "ml": Domain.AI_ML,
    "artificial intelligence": Domain.AI_ML,
    "digital marketing": Domain.DIGITAL_MARKETING,
    "ui/ux": Domain.UI_UX,
    "ui ux": Domain.UI_UX,
    "uiux": Domain.UI_UX,
    "uix": Domain.UI_UX,
}

DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
    "%m/%d/%y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
)

TIME_SHIFT_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]")

router = APIRouter(prefix="/import", tags=["excel"])


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _text(value: Any, max_len: Optional[int] = None) -> Optional[str]:
    if _is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    s = str(value).strip()
    if max_len is not None:
        s = s[:max_len]
    return s or None


def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=int(value))).date()
        except (ValueError, OverflowError):
            return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return (datetime(1899, 12, 30) + timedelta(days=int(float(s)))).date()
    except (ValueError, OverflowError):
        return None


def _normalize_status(value: Any) -> Optional[LaptopStatus]:
    if _is_blank(value):
        return None
    return STATUS_NORMALIZE.get(str(value).strip().lower())


def _normalize_batch(value: Any) -> Optional[Batch]:
    if _is_blank(value):
        return None
    return BATCH_ALIASES.get(str(value).strip().lower())


def _normalize_domain(value: Any) -> Optional[Domain]:
    if _is_blank(value):
        return None
    return DOMAIN_ALIASES.get(str(value).strip().lower())


def _parse_time_shift(value: Any) -> Tuple[Optional[dtime], Optional[dtime]]:
    if _is_blank(value):
        return None, None
    matches = TIME_SHIFT_RE.findall(str(value))
    if len(matches) < 2:
        return None, None

    def to_time(parts: Tuple[str, str, str]) -> dtime:
        hour = int(parts[0])
        minute = int(parts[1] or 0)
        period = parts[2].lower()
        if period == "pm" and hour < 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        return dtime(hour, minute)

    return to_time(matches[0]), to_time(matches[-1])


def _default_times(batch: Batch) -> Tuple[dtime, dtime]:
    if batch == Batch.AFTERNOON:
        return dtime(14, 0), dtime(18, 0)
    if batch == Batch.FULL_DAY:
        return dtime(9, 0), dtime(18, 0)
    return dtime(9, 0), dtime(13, 0)


def _normalize_header(value: Any) -> Optional[str]:
    if _is_blank(value):
        return None
    return " ".join(str(value).strip().lower().split())


def _header_key(value: Any) -> str:
    """Compact, case-insensitive header key for matching column aliases.
    Spaces, underscores, hyphens and punctuation are ignored so "Laptop ID",
    "Laptop_ID", "laptop id" and "laptop-id" all reduce to the same key."""
    return _SLUG_RE.sub("", _normalize_header(value) or "")


_KNOWN_HEADER_KEYS = {
    _header_key(alias) for aliases in COLUMN_MAP.values() for alias in aliases
}


def _map_headers(raw_headers: List[Any]) -> Tuple[Dict[str, str], List[str]]:
    """Return (canonical -> compact header key, compact header keys of the file)."""
    normalized = [_header_key(h) for h in raw_headers]
    lookup: Dict[str, str] = {}
    for canonical, aliases in COLUMN_MAP.items():
        for alias in aliases:
            key = _header_key(alias)
            if key in normalized:
                lookup[canonical] = key
                break
    return lookup, normalized


def _header_positions(raw_headers: List[Any], header_map: Dict[str, str]) -> Dict[int, str]:
    """Map each header column index to its canonical field name."""
    positions: Dict[int, str] = {}
    recognized_headers = set(header_map.values())
    for col_index, cell in enumerate(raw_headers):
        norm = _header_key(cell)
        if norm in recognized_headers:
            positions[col_index] = next(
                canonical for canonical, header in header_map.items() if header == norm
            )
    return positions


def _row_dict(raw_row: List[Any], positions: Dict[int, str]) -> Dict[str, Any]:
    """Extract canonical field values from a data row using the header positions."""
    values = list(raw_row or [])
    return {
        canonical: values[col_index]
        for col_index, canonical in positions.items()
        if col_index < len(values)
    }


_FIRST_WINS_FIELDS = (
    "brand", "model", "serial_number", "processor", "ram", "storage",
    "operating_system", "status",
)
_LAST_WINS_FIELDS = (
    "domain", "department", "time_shift", "batch",
    "intern_id", "intern_name", "email", "phone",
)


def _merge_sheet_row(acc: Dict[str, Any], row: Dict[str, Any], sheet_name: str) -> None:
    """Merge one sheet's row into the accumulated record for the same Laptop ID.

    First sheet wins for hardware/status fields (so "Overall Stock", processed
    first, is authoritative), while assignment/person fields ("Master
    allocation", processed last) win for domain / intern details."""
    for field in _FIRST_WINS_FIELDS:
        if _is_blank(acc.get(field)) and not _is_blank(row.get(field)):
            acc[field] = row.get(field)
    for field in _LAST_WINS_FIELDS:
        if not _is_blank(row.get(field)):
            acc[field] = row.get(field)


# ---------------------------------------------------------------------------
# Workbook reading — ALL worksheets are read, not just the first one.
# Each sheet's header row is auto-detected (tolerant of title rows such as
# "ACADEMY LAPTOPS" above the real header) and column aliases are matched
# case/whitespace/underscore-insensitively.
# ---------------------------------------------------------------------------
@dataclass
class SheetTable:
    name: str
    header: List[Any]
    rows: List[List[Any]]


def _cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _read_all_sheets(data: bytes, ext: str) -> List[SheetTable]:
    if ext == ".xls":
        raw_sheets = _read_xls_sheets(data)
    else:
        raw_sheets = _read_xlsx_sheets(data)

    tables: List[SheetTable] = []
    for name, raw_rows in raw_sheets:
        header_index = _detect_header_index(raw_rows)
        if header_index is None:
            logger.info("Sheet '%s' skipped — no recognized header row found", name)
            continue
        header = [_cell(c) for c in raw_rows[header_index]]
        data_rows = _prune_rows(
            [[_cell(c) for c in r] for r in raw_rows[header_index + 1 :]]
        )
        tables.append(SheetTable(name=name, header=header, rows=data_rows))
        logger.info(
            "Sheet '%s' parsed: %d data row(s), header %s",
            name,
            len(data_rows),
            header,
        )
    return tables


def _read_xlsx_sheets(data: bytes) -> List[Tuple[str, List[List[Any]]]]:
    try:
        wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file format. Could not read the Excel workbook.")
    try:
        if not wb.sheetnames:
            raise HTTPException(status_code=422, detail="Excel file contains no worksheets.")
        return [
            (sn, [list(r) for r in wb[sn].iter_rows(values_only=True)])
            for sn in wb.sheetnames
        ]
    finally:
        wb.close()


def _read_xls_sheets(data: bytes) -> List[Tuple[str, List[List[Any]]]]:
    try:
        import xlrd

        book = xlrd.open_workbook(file_contents=data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file format. Could not read the Excel workbook.")
    if book.nsheets == 0:
        raise HTTPException(status_code=422, detail="Excel file contains no worksheets.")

    sheets: List[Tuple[str, List[List[Any]]]] = []
    for si in range(book.nsheets):
        sheet = book.sheet_by_index(si)
        rows: List[List[Any]] = []
        for r in range(sheet.nrows):
            row: List[Any] = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                ctype = cell.ctype
                if ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
                elif ctype == xlrd.XL_CELL_NUMBER and float(cell.value).is_integer():
                    row.append(int(cell.value))
                else:
                    row.append(cell.value)
            rows.append(row)
        sheets.append((book.sheet_names()[si], rows))
    return sheets


def _detect_header_index(raw_rows: List[List[Any]]) -> Optional[int]:
    """Find the first row that contains at least one recognized header cell."""
    for idx, row in enumerate(raw_rows):
        for cell in row:
            if not _is_blank(cell) and _header_key(cell) in _KNOWN_HEADER_KEYS:
                return idx
    return None


def _prune_rows(rows: List[List[Any]]) -> List[List[Any]]:
    return [list(r) for r in rows if any(not _is_blank(cell) for cell in r)]


# ---------------------------------------------------------------------------
# Upsert helpers. Each runs inside its caller's SAVEPOINT (`begin_nested`).
# A ValueError raised here is converted into a row-level import error.
# ---------------------------------------------------------------------------
def _upsert_laptop(db: Session, row: Dict[str, Any], cache: Dict[str, Any], meta: ImportRow) -> Optional[Laptop]:
    tag = _text(row.get("asset_tag"), 20)
    serial = _text(row.get("serial_number"), 100)
    if not tag and not serial:
        return None

    obj: Optional[Laptop] = None
    if tag:
        obj = cache["by_number"].get(tag) or db.query(Laptop).filter(Laptop.laptop_number == tag).first()
    if not obj and serial:
        obj = cache["by_serial"].get(serial) or db.query(Laptop).filter(Laptop.serial_number == serial).first()

    if obj is None and tag and serial:
        by_number = db.query(Laptop).filter(Laptop.laptop_number == tag).first()
        by_serial = db.query(Laptop).filter(Laptop.serial_number == serial).first()
        if by_number and by_serial and by_number.id != by_serial.id:
            raise ValueError(f"Asset Tag '{tag}' and Serial Number '{serial}' match different laptops")

    if obj is None:
        if not tag:
            raise ValueError("Laptop ID is required to create a new laptop")
        obj = Laptop(
            laptop_number=tag,
            serial_number=serial or tag,
            brand="",
            model="",
            status=LaptopStatus.FREE,
        )
        db.add(obj)
        meta.inserted = True
    else:
        if tag and obj.laptop_number != tag:
            obj.laptop_number = tag
            meta.updated = True
        if serial and obj.serial_number != serial:
            obj.serial_number = serial
            meta.updated = True

    for field in ("brand", "model", "processor", "ram", "storage", "operating_system"):
        limit = 50 if field == "brand" else 100
        value = _text(row.get(field), limit)
        if value is not None and getattr(obj, field) != value:
            setattr(obj, field, value)
            meta.updated = True

    status = _normalize_status(row.get("status"))
    if status is not None and obj.status != status:
        obj.status = status
        meta.updated = True

    cache["by_number"][obj.laptop_number] = obj
    if obj.serial_number:
        cache["by_serial"][obj.serial_number] = obj
    db.flush()
    return obj


def _slug(name: str) -> str:
    return _SLUG_RE.sub("", name.lower()) or "intern"


def _upsert_intern(db: Session, row: Dict[str, Any], cache: Dict[str, Any], meta: ImportRow) -> Optional[Intern]:
    intern_id = _text(row.get("intern_id"), 20)
    name = _text(row.get("intern_name"), 100)
    email = _text(row.get("email"), 100)
    if not intern_id and not name:
        return None
    # The intern is only strictly REQUIRED when this row also creates an
    # allocation. Without an allocation, a missing/invalid intern detail must
    # not block the laptop itself from being imported (the laptop stays
    # unassigned and the reason is logged instead of failing the row).
    will_allocate = _to_date(row.get("allocation_date")) is not None

    obj: Optional[Intern] = None
    if intern_id:
        obj = cache["by_id"].get(intern_id) or db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not obj and email:
        obj = cache["by_email"].get(email) or db.query(Intern).filter(Intern.email == email).first()
    if not obj and name:
        name_key = name.strip().lower()
        obj = (
            cache["by_name"].get(name_key)
            or db.query(Intern).filter(func.lower(Intern.name) == name_key).first()
        )

    raw_domain = _text(row.get("domain") or row.get("department"), 50)
    domain = _normalize_domain(raw_domain)

    batch = _normalize_batch(row.get("batch"))
    if batch is None:
        start_time, _ = _parse_time_shift(row.get("time_shift"))
        batch = Batch.AFTERNOON if (start_time and start_time.hour >= 12) else Batch.MORNING

    if obj is None:
        if not name:
            if will_allocate:
                raise ValueError("Intern Name is required to create a new intern")
            logger.info("Intern record skipped — name is blank (laptop '%s' imported unassigned)", intern_id or "")
            return None
        if domain is None:
            if will_allocate:
                raise ValueError(f"Invalid Domain value: {raw_domain or '(missing)'}")
            logger.info(
                "Intern record for '%s' skipped — invalid/unknown domain '%s' is not one of %s",
                name,
                raw_domain or "(missing)",
                ", ".join(DOMAIN_OPTIONS),
            )
            return None
        intern_id = intern_id or f"INT-{_slug(name)[:15]}".upper()
        email = email or f"{_slug(name)[:20]}@interns.com"
        email = email.lower()
        if db.query(Intern).filter(Intern.intern_id == intern_id).first():
            if will_allocate:
                raise ValueError(f"Intern ID '{intern_id}' is already in the database")
            logger.info("Intern ID '%s' already exists — skipping auto-generated intern record", intern_id)
            return None
        phone = _text(row.get("phone"), 20) or "0000000000"
        obj = Intern(
            intern_id=intern_id,
            name=name,
            email=email,
            phone=phone,
            batch=batch,
            domain=domain,
        )
        db.add(obj)
        meta.inserted = True
    else:
        if intern_id and obj.intern_id != intern_id:
            obj.intern_id = intern_id
            meta.updated = True
        if name and obj.name != name:
            obj.name = name
            meta.updated = True
        if email and obj.email != email:
            obj.email = email
            meta.updated = True
        phone = _text(row.get("phone"), 20)
        if phone and obj.phone != phone:
            obj.phone = phone
            meta.updated = True
        if domain is not None and obj.domain != domain:
            obj.domain = domain
            meta.updated = True
        if batch is not None and obj.batch != batch:
            obj.batch = batch
            meta.updated = True

    if obj.intern_id and obj.email:
        cache["by_id"][obj.intern_id] = obj
        cache["by_email"][obj.email] = obj
    if obj.name:
        cache["by_name"][obj.name.lower()] = obj
    db.flush()
    return obj


def _upsert_allocation(
    db: Session,
    row: Dict[str, Any],
    laptop: Laptop,
    intern: Intern,
    meta: ImportRow,
) -> Optional[Allocation]:
    allocation_date = _to_date(row.get("allocation_date"))
    if not allocation_date:
        return None

    return_date = _to_date(row.get("return_date"))
    if return_date and return_date < allocation_date:
        raise ValueError("Return Date is before the Allocation Date")

    start_time, end_time = _parse_time_shift(row.get("time_shift"))
    if not start_time or not end_time:
        start_time, end_time = _default_times(intern.batch)

    obj = (
        db.query(Allocation)
        .filter(
            Allocation.laptop_id == laptop.id,
            Allocation.allocation_date == allocation_date,
        )
        .first()
    )

    if obj is None:
        status = AllocationStatus.RETURNED if return_date else AllocationStatus.ACTIVE
        obj = Allocation(
            laptop_id=laptop.id,
            intern_id=intern.id,
            batch=intern.batch.value,
            domain=intern.domain.value,
            allocation_date=allocation_date,
            start_time=start_time,
            end_time=end_time,
            status=status,
            returned_at=return_date,
        )
        db.add(obj)
        meta.inserted = True
    else:
        if obj.intern_id != intern.id:
            obj.intern_id = intern.id
            meta.updated = True
        if obj.start_time != start_time or obj.end_time != end_time:
            obj.start_time = start_time
            obj.end_time = end_time
            meta.updated = True
        if obj.batch != intern.batch.value:
            obj.batch = intern.batch.value
            meta.updated = True
        if obj.domain != intern.domain.value:
            obj.domain = intern.domain.value
            meta.updated = True
        if return_date:
            new_status = AllocationStatus.RETURNED
            if obj.status != new_status or obj.returned_at != return_date:
                obj.status = new_status
                obj.returned_at = return_date
                meta.updated = True
        else:
            if obj.status != AllocationStatus.ACTIVE:
                obj.status = AllocationStatus.ACTIVE
                obj.returned_at = None
                meta.updated = True

    # Keep the laptop status consistent with its allocation: a laptop with an
    # ACTIVE allocation is ALLOCATED, a returned allocation frees it.
    if obj.status == AllocationStatus.ACTIVE and laptop.status != LaptopStatus.ALLOCATED:
        laptop.status = LaptopStatus.ALLOCATED
        meta.updated = True
    elif (
        obj.status == AllocationStatus.RETURNED
        and laptop.status == LaptopStatus.ALLOCATED
    ):
        laptop.status = LaptopStatus.FREE
        meta.updated = True

    db.flush()
    return obj


# ---------------------------------------------------------------------------
# Import endpoint
# ---------------------------------------------------------------------------
@router.post("/excel", response_model=ImportSummary)
def import_excel(
    file: UploadFile = File(..., description="Excel file (.xlsx or .xls)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    ext = path.splitext(filename)[1].lower() or ".xlsx"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload a .xlsx or .xls Excel file.",
        )

    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Excel file exceeds the maximum allowed size (10 MB).",
        )

    tables = _read_all_sheets(raw, ext)
    if not tables:
        raise HTTPException(status_code=422, detail="Excel file contains no data rows.")

    # Sheets are processed in priority order. "Overall Stock" is the master
    # inventory; the other sheets supplement brand/domain/intern details and
    # status (In Hand -> FREE, Hand Over -> ALLOCATED). Rows are merged per
    # unique Laptop ID so every record in every sheet contributes to the same
    # database row and nothing is imported twice.
    _SHEET_PRIORITY_ORDER = [
        "Overall Stock", "In Hand", "Hand Over", "Master allocation", "Asset Stock",
    ]
    _SHEET_PRIORITY = {
        name.lower(): i for i, name in enumerate(_SHEET_PRIORITY_ORDER)
    }

    def _sheet_priority(name: str) -> int:
        return _SHEET_PRIORITY.get(name.strip().lower(), len(_SHEET_PRIORITY_ORDER))

    merged: Dict[str, Tuple[Dict[str, Any], int]] = {}
    order_ok = False
    for table in sorted(tables, key=lambda t: _sheet_priority(t.name)):
        header_map, _ = _map_headers(table.header)
        has_identifier = any(k in header_map for k in ("asset_tag", "serial_number", "intern_id", "intern_name"))
        if not has_identifier:
            logger.info("Sheet '%s' skipped — no laptop/intern identifier column matched", table.name)
            continue
        positions = _header_positions(table.header, header_map)
        order_ok = True
        for data_index, raw_row in enumerate(table.rows):
            row = _row_dict(raw_row, positions)
            asset = _text(row.get("asset_tag"), 20)
            if not asset:
                continue
            key = asset.upper()
            row_no = data_index + 2  # header is row 1 in the spreadsheet
            if key not in merged:
                merged[key] = (dict(row), row_no)
            else:
                acc, _ = merged[key]
                _merge_sheet_row(acc, row, table.name)

    if not order_ok or not merged:
        raise HTTPException(
            status_code=422,
            detail="Required columns not found. At least one laptop identifier "
            "(Laptop ID, Laptop Name, Asset, Serial Number) or intern identifier "
            "(Intern ID, Intern Name) column is required.",
        )

    rows_read = sum(len(t.rows) for t in tables)
    sheets_read = len(tables)
    total_rows = len(merged)

    cache: Dict[str, Dict[str, Any]] = {
        "by_number": {},
        "by_serial": {},
        "by_id": {},
        "by_email": {},
        "by_name": {},
    }

    inserted = 0
    updated = 0
    duplicates = 0
    invalid = 0
    partial = 0
    errors: List[ImportRowError] = []

    for key, (row, row_no) in merged.items():
        meta = ImportRow()
        has_intern_input = any(
            not _is_blank(row.get(k)) for k in ("intern_id", "intern_name")
        )
        intern = None
        try:
            with db.begin_nested():
                laptop = _upsert_laptop(db, row, cache, meta)
                if has_intern_input:
                    intern = _upsert_intern(db, row, cache, meta)
                if laptop and intern:
                    _upsert_allocation(db, row, laptop, intern, meta)
        except ValueError as exc:
            invalid += 1
            errors.append(ImportRowError(row=row_no, error=str(exc)))
            logger.info("Row %d (%s) skipped: %s", row_no, key, exc)
            continue
        except IntegrityError:
            invalid += 1
            errors.append(
                ImportRowError(
                    row=row_no,
                    error="Duplicate record or database constraint violation",
                )
            )
            logger.info("Row %d (%s) skipped: database constraint violation", row_no, key)
            continue

        if meta.inserted:
            inserted += 1
        elif meta.updated:
            updated += 1
        else:
            duplicates += 1

        if has_intern_input and intern is None:
            partial += 1
            errors.append(
                ImportRowError(
                    row=row_no,
                    error=(
                        f"Intern record skipped for laptop {key} (laptop still "
                        f"imported): name or domain missing/blank/"
                        f"invalid. Laptop {key} is stored unassigned."
                    ),
                )
            )

    db.commit()

    laptops_total = db.query(Laptop).count()
    interns_total = db.query(Intern).count()

    skipped = duplicates + invalid + partial
    if inserted == 0 and updated == 0 and invalid == 0:
        return ImportSummary(
            success=True,
            message="Excel import completed. No changes were needed — all records already existed.",
            total_rows=total_rows,
            inserted=0,
            updated=0,
            duplicates=duplicates,
            invalid=0,
            skipped=skipped,
            errors=[],
            rows_read=rows_read,
            sheets_read=sheets_read,
            laptops_total=laptops_total,
            interns_total=interns_total,
        )

    if inserted == 0 and updated == 0:
        if duplicates == 0:
            return ImportSummary(
                success=False,
                message="No records were imported. Please review the validation errors.",
                total_rows=total_rows,
                inserted=0,
                updated=0,
                duplicates=0,
                invalid=invalid,
                skipped=skipped,
                errors=errors,
                rows_read=rows_read,
                sheets_read=sheets_read,
                laptops_total=laptops_total,
                interns_total=interns_total,
            )
        return ImportSummary(
            success=True,
            message=f"Excel import completed — {duplicates} duplicate(s) skipped, {invalid} invalid row(s).",
            total_rows=total_rows,
            inserted=0,
            updated=0,
            duplicates=duplicates,
            invalid=invalid,
            skipped=skipped,
            errors=errors,
            rows_read=rows_read,
            sheets_read=sheets_read,
            laptops_total=laptops_total,
            interns_total=interns_total,
        )

    parts = [f"{inserted} added", f"{updated} updated"]
    if duplicates:
        parts.append(f"{duplicates} duplicates")
    if invalid:
        parts.append(f"{invalid} invalid row(s) skipped")
    if partial:
        parts.append(f"{partial} intern detail(s) skipped")
    message = "Excel imported successfully — " + ", ".join(parts) + "."
    return ImportSummary(
        success=True,
        message=message,
        total_rows=total_rows,
        inserted=inserted,
        updated=updated,
        duplicates=duplicates,
        invalid=invalid,
        skipped=skipped,
        errors=errors,
        rows_read=rows_read,
        sheets_read=sheets_read,
        laptops_total=laptops_total,
        interns_total=interns_total,
    )


# ---------------------------------------------------------------------------
# XLSX helpers (shared by template + export)
# ---------------------------------------------------------------------------
def _write_table(ws, headers: List[str], rows: List[List[Any]], widths: Optional[Dict[str, int]] = None) -> None:
    ws.append(headers)
    for row in rows:
        ws.append(row)

    header_fill = PatternFill("solid", fgColor="1D4ED8")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    if rows:
        last_col = get_column_letter(len(headers))
        last_row = len(rows) + 1
        ws.auto_filter.ref = f"A1:{last_col}{last_row}"
        ws.freeze_panes = "A2"

    if widths:
        for col_letter, width in widths.items():
            ws.column_dimensions[col_letter].width = width


def _format_date_columns(ws, date_columns: List[str], total_rows: int) -> None:
    for col_letter in date_columns:
        for row_index in range(2, total_rows + 2):
            cell = ws[f"{col_letter}{row_index}"]
            cell.number_format = DATE_FORMAT


# ---------------------------------------------------------------------------
# Export endpoint  —  Laptop Allocation Report / Summary / Instructions
# ---------------------------------------------------------------------------
REPORT_HEADERS = [
    "Laptop ID", "Brand", "Model", "Serial Number", "RAM", "Storage",
    "Laptop Status", "Intern ID", "Intern Name", "Email", "Domain",
    "Allocation Date", "Return Date", "Allocation Status",
]

REPORT_WIDTHS = {
    "A": 14, "B": 12, "C": 20, "D": 16, "E": 10, "F": 14, "G": 14,
    "H": 12, "I": 20, "J": 28, "K": 18, "L": 15, "M": 15, "N": 18,
}


def _report_rows(db: Session) -> List[List[Any]]:
    laptops = db.query(Laptop).order_by(Laptop.laptop_number).all()
    interns_by_id = {i.id: i for i in db.query(Intern).all()}
    allocs = (
        db.query(Allocation)
        .order_by(Allocation.allocation_date.desc(), Allocation.created_at.desc())
        .all()
    )
    grouped: Dict[int, List[Allocation]] = defaultdict(list)
    for a in allocs:
        grouped[a.laptop_id].append(a)

    rows: List[List[Any]] = []
    for laptop in laptops:
        laptop_base = [
            laptop.laptop_number, laptop.brand, laptop.model, laptop.serial_number,
            laptop.ram or "", laptop.storage or "", laptop.status.value,
        ]
        lap_allocs = grouped.get(laptop.id, [])
        if not lap_allocs:
            rows.append(laptop_base + ["", "", "", "", "", "", ""])
            continue
        for a in lap_allocs:
            intern = interns_by_id.get(a.intern_id) if a.intern_id else None
            rows.append(
                laptop_base
                + [
                    intern.intern_id if intern else "",
                    intern.name if intern else "",
                    intern.email if intern else "",
                    a.domain or "",
                    a.allocation_date,
                    a.returned_at.date() if a.returned_at else None,
                    a.status.value,
                ]
            )
    return rows


def _summary_rows(db: Session) -> List[List[Any]]:
    counts = {
        "total_laptops": db.query(Laptop).count(),
        "free_laptops": db.query(Laptop).filter(Laptop.status == LaptopStatus.FREE).count(),
        "allocated_laptops": db.query(Laptop).filter(Laptop.status == LaptopStatus.ALLOCATED).count(),
        "maintenance_laptops": db.query(Laptop).filter(Laptop.status == LaptopStatus.MAINTENANCE).count(),
        "inactive_laptops": db.query(Laptop).filter(Laptop.status == LaptopStatus.INACTIVE).count(),
        "total_interns": db.query(Intern).count(),
        "total_allocations": db.query(Allocation).count(),
        "active_allocations": db.query(Allocation).filter(Allocation.status == AllocationStatus.ACTIVE).count(),
        "returned_allocations": db.query(Allocation).filter(Allocation.status == AllocationStatus.RETURNED).count(),
        "cancelled_allocations": db.query(Allocation).filter(Allocation.status == AllocationStatus.CANCELLED).count(),
        "completed_allocations": db.query(Allocation).filter(Allocation.status == AllocationStatus.COMPLETED).count(),
    }

    labels = {
        "total_laptops": "Total Laptops",
        "free_laptops": "Free Laptops",
        "allocated_laptops": "Allocated Laptops",
        "maintenance_laptops": "Maintenance Laptops",
        "inactive_laptops": "Inactive Laptops",
        "total_interns": "Total Interns",
        "total_allocations": "Total Allocations",
        "active_allocations": "Active Allocations",
        "returned_allocations": "Returned Allocations",
        "cancelled_allocations": "Cancelled Allocations",
        "completed_allocations": "Completed Allocations",
    }

    rows: List[List[Any]] = [["Metric", "Value"]]
    for key, value in counts.items():
        rows.append([labels[key], value])

    domain_rows = (
        db.query(Allocation.domain, func.count(Allocation.id))
        .group_by(Allocation.domain)
        .order_by(func.count(Allocation.id).desc())
        .all()
    )
    for domain, value in domain_rows:
        rows.append([f"Domain: {domain or 'Unknown'}", value])

    return rows


def _build_export_workbook(db: Session) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()

    # Sheet 1 — Laptop Allocation Report
    ws = wb.active
    ws.title = "Laptop Allocation Report"
    report = _report_rows(db)
    _write_table(ws, REPORT_HEADERS, report, REPORT_WIDTHS)
    _format_date_columns(ws, ["L", "M"], len(report))

    # Sheet 2 — Summary
    ws2 = wb.create_sheet("Summary")
    _write_table(ws2, ["Metric", "Value"], _summary_rows(db)[1:], {"A": 30, "B": 16})
    ws2.freeze_panes = "A2"

    # Sheet 3 — Instructions
    ws3 = wb.create_sheet("Instructions")
    instructions = [
        ["About this workbook", ""],
        ["", ""],
        [
            "Laptop Allocation Report",
            "One row per laptop allocation. Laptops without an allocation appear with blank allocation fields.",
        ],
        [
            "Summary",
            "Current inventory, allocation and domain statistics computed from the live database.",
        ],
        ["", ""],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
    ]
    for row in instructions:
        ws3.append(row)
    ws3.column_dimensions["A"].width = 26
    ws3.column_dimensions["B"].width = 90

    return wb


# ---------------------------------------------------------------------------
# Template endpoint
# ---------------------------------------------------------------------------
def _build_template_workbook() -> openpyxl.Workbook:
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "Import Template"
    _write_table(ws, TEMPLATE_HEADERS, [TEMPLATE_SAMPLE], TEMPLATE_WIDTHS)
    _format_date_columns(ws, ["L", "M"], 1)

    domain_validation = DataValidation(
        type="list",
        formula1='"' + ",".join(DOMAIN_OPTIONS) + '"',
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Invalid Domain",
        error="Domain must be one of: Cloud, Data Analytics, Full Stack, AI & ML, Digital Marketing, UI/UX.",
    )
    status_validation = DataValidation(
        type="list",
        formula1='"' + ",".join(STATUS_OPTIONS) + '"',
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Invalid Status",
        error="Status must be one of: FREE, ALLOCATED, MAINTENANCE, INACTIVE.",
    )
    ws.add_data_validation(domain_validation)
    ws.add_data_validation(status_validation)

    # Example row is row 2; allow dropdowns for any future data rows.
    domain_validation.add("K2:K1000")
    status_validation.add("N2:N1000")

    notes = wb.create_sheet("Instructions")
    instructions = [
        ["Instructions", ""],
        ["", ""],
        ["How to use", "Fill the columns on the 'Import Template' sheet. One record per row — you can import laptops only, laptops + interns, or a full allocation."],
        ["", ""],
        ["Laptop ID / Laptop Name", "Any one is enough to create or update a laptop. This value becomes the laptop number."],
        ["Brand / Model", "Left blank (empty) on new laptops when the Excel file has no Brand / Model column."],
        ["Serial Number", "Used to detect and update an existing laptop when Laptop ID is blank."],
        ["RAM / Storage", "Plain text such as '16 GB' or '512 GB SSD'."],
        ["Intern ID / Intern Name", "Interns are created or updated from these columns. Intern Name is required for a new intern."],
        ["Email", "Used to match an existing intern. A placeholder is generated when blank."],
        ["Domain", "Drop-down list. Valid values: Cloud, Data Analytics, Full Stack, AI & ML, Digital Marketing, UI/UX."],
        ["Allocation Date / Return Date", "Creates or updates an allocation. Return Date must not be before Allocation Date. Empty Allocation Date skips allocation import."],
        ["Status", "Drop-down list. Valid values: FREE, ALLOCATED, MAINTENANCE, INACTIVE."],
        ["", ""],
        ["Notes", "Only the first worksheet of the file is read. Max upload size is 10 MB. Rows with validation errors are skipped; everything else is saved."],
        ["Date formats", "2026-09-08, 08/09/2026, 08-09-2026 and native Excel date cells are accepted."],
    ]
    for row in instructions:
        notes.append(row)
    notes.column_dimensions["A"].width = 38
    notes.column_dimensions["B"].width = 95

    return wb


export_router = APIRouter(prefix="/export", tags=["excel"])


@export_router.get("/excel")
def export_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wb = _build_export_workbook(db)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type=EXPORT_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="laptop_allocations_export.xlsx"'
        },
    )


@export_router.get("/template")
def download_template(
    current_user: User = Depends(get_current_user),
):
    wb = _build_template_workbook()
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type=EXPORT_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="laptop_import_template.xlsx"'
        },
    )