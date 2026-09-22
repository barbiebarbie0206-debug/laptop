from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional
from io import StringIO
import csv as csv_module
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.allocation import Allocation, AllocationStatus
from ..models.laptop import Laptop, LaptopStatus
from ..models.intern import Intern, Batch, Domain
from ..models.user import User
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date, time, timedelta, timezone


class LaptopAvailableResponse(BaseModel):
    id: int
    laptop_number: str
    brand: str
    model: str
    serial_number: str

    model_config = ConfigDict(from_attributes=True)


class AllocatableInternResponse(BaseModel):
    id: int
    intern_id: str
    name: str
    email: str
    phone: str
    batch: str
    domain: str
    has_active_allocation: bool

    model_config = ConfigDict(from_attributes=True)


class AllocationCreate(BaseModel):
    laptop_id: int
    intern_id: int
    allocation_date: date
    start_time: time
    end_time: time


class AllocationResponse(BaseModel):
    id: int
    laptop_id: int
    intern_id: int
    laptop_number: Optional[str] = None
    intern_name: Optional[str] = None
    batch: Optional[str] = None
    domain: Optional[str] = None
    allocation_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    returned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ActionResponse(BaseModel):
    allocation_id: int
    laptop_number: str
    intern_name: str
    status: str
    message: str


class AllocationPageResponse(BaseModel):
    items: List[AllocationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DomainStat(BaseModel):
    domain: str
    total_allocations: int
    active_allocations: int
    returned_allocations: int
    cancelled_allocations: int


class ReportsResponse(BaseModel):
    total_allocations: int
    active_allocations: int
    returned_allocations: int
    cancelled_allocations: int
    morning_allocations: int
    afternoon_allocations: int
    full_day_allocations: int
    unique_laptops_used: int
    unique_interns: int
    total_laptops: int
    total_interns: int
    free_laptops: int
    domain_stats: List[DomainStat]


router = APIRouter(prefix="/allocations", tags=["allocations"])


def _apply_filters(
    query,
    db: Session,
    allocation_date: Optional[date] = None,
    batch: Optional[str] = None,
    domain: Optional[str] = None,
    laptop_number: Optional[str] = None,
    intern_name: Optional[str] = None,
    status: Optional[AllocationStatus] = None,
    search: Optional[str] = None,
):
    if allocation_date:
        query = query.filter(Allocation.allocation_date == allocation_date)
    if batch:
        query = query.filter(Allocation.batch == batch)
    if domain:
        query = query.filter(Allocation.domain == domain)
    if status:
        query = query.filter(Allocation.status == status)

    if laptop_number:
        laptop_ids = [
            l.id for l in db.query(Laptop).filter(Laptop.laptop_number.ilike(f"%{laptop_number}%")).all()
        ]
        query = query.filter(Allocation.laptop_id.in_(laptop_ids) if laptop_ids else Allocation.laptop_id == -1)

    if intern_name:
        intern_ids = [
            i.id for i in db.query(Intern).filter(Intern.name.ilike(f"%{intern_name}%")).all()
        ]
        query = query.filter(Allocation.intern_id.in_(intern_ids) if intern_ids else Allocation.intern_id == -1)

    if search:
        search_term = f"%{search}%"
        laptop_ids = [l.id for l in db.query(Laptop).filter(Laptop.laptop_number.ilike(search_term)).all()]
        intern_ids = [i.id for i in db.query(Intern).filter(Intern.name.ilike(search_term)).all()]
        id_conditions = []
        if laptop_ids:
            id_conditions.append(Allocation.laptop_id.in_(laptop_ids))
        if intern_ids:
            id_conditions.append(Allocation.intern_id.in_(intern_ids))
        if id_conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*id_conditions))
        else:
            query = query.filter(Allocation.laptop_id == -1)

    return query


def _serialize(allocation: Allocation, db: Session) -> AllocationResponse:
    laptop = db.query(Laptop).filter(Laptop.id == allocation.laptop_id).first()
    intern = db.query(Intern).filter(Intern.id == allocation.intern_id).first()
    return AllocationResponse(
        id=allocation.id,
        laptop_id=allocation.laptop_id,
        intern_id=allocation.intern_id,
        laptop_number=laptop.laptop_number if laptop else None,
        intern_name=intern.name if intern else None,
        batch=allocation.batch,
        domain=allocation.domain if allocation.domain else (intern.domain.value if intern else None),
        allocation_date=allocation.allocation_date,
        start_time=allocation.start_time.strftime("%H:%M") if allocation.start_time else None,
        end_time=allocation.end_time.strftime("%H:%M") if allocation.end_time else None,
        status=allocation.status.value,
        returned_at=allocation.returned_at,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


@router.get("/available-laptops", response_model=List[LaptopAvailableResponse])
def get_available_laptops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_ids = [
        a.laptop_id
        for a in db.query(Allocation).filter(Allocation.status == AllocationStatus.ACTIVE).all()
    ]
    query = db.query(Laptop).filter(Laptop.status == LaptopStatus.FREE)
    if active_ids:
        query = query.filter(~Laptop.id.in_(active_ids))
    laptops = query.order_by(Laptop.laptop_number).all()
    return [
        LaptopAvailableResponse(
            id=l.id,
            laptop_number=l.laptop_number,
            brand=l.brand,
            model=l.model,
            serial_number=l.serial_number,
        )
        for l in laptops
    ]


@router.get("/allocatable-interns", response_model=List[AllocatableInternResponse])
def get_allocatable_interns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_intern_ids = {
        a.intern_id
        for a in db.query(Allocation).filter(Allocation.status == AllocationStatus.ACTIVE).all()
    }
    interns = db.query(Intern).order_by(Intern.intern_id).all()
    return [
        AllocatableInternResponse(
            id=i.id,
            intern_id=i.intern_id,
            name=i.name,
            email=i.email,
            phone=i.phone,
            batch=i.batch.value,
            domain=i.domain.value,
            has_active_allocation=i.id in active_intern_ids,
        )
        for i in interns
    ]


@router.get("/", response_model=List[AllocationResponse])
def get_allocations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[AllocationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Allocation)
    if status:
        query = query.filter(Allocation.status == status)
    allocations = query.order_by(Allocation.created_at.desc()).offset(skip).limit(limit).all()
    return [_serialize(a, db) for a in allocations]


@router.get("/active", response_model=List[AllocationResponse])
def get_active_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocations = (
        db.query(Allocation)
        .filter(Allocation.status == AllocationStatus.ACTIVE)
        .order_by(Allocation.created_at.desc())
        .all()
    )
    return [_serialize(a, db) for a in allocations]


@router.get("/history", response_model=AllocationPageResponse)
def get_allocation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    allocation_date: Optional[date] = None,
    batch: Optional[str] = None,
    domain: Optional[str] = None,
    laptop_number: Optional[str] = None,
    intern_name: Optional[str] = None,
    status: Optional[AllocationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Allocation)
    query = _apply_filters(
        query,
        db,
        allocation_date=allocation_date,
        batch=batch,
        domain=domain,
        laptop_number=laptop_number,
        intern_name=intern_name,
        status=status,
        search=search,
    )
    total = query.count()
    query = query.order_by(Allocation.allocation_date.desc(), Allocation.created_at.desc())
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total else 0
    return AllocationPageResponse(
        items=[_serialize(a, db) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/reports", response_model=ReportsResponse)
def get_reports(
    allocation_date: Optional[date] = None,
    batch: Optional[str] = None,
    domain: Optional[str] = None,
    laptop_number: Optional[str] = None,
    intern_name: Optional[str] = None,
    status: Optional[AllocationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Allocation)
    query = _apply_filters(
        query,
        db,
        allocation_date=allocation_date,
        batch=batch,
        domain=domain,
        laptop_number=laptop_number,
        intern_name=intern_name,
        status=status,
    )

    total = query.count()
    active = query.filter(Allocation.status == AllocationStatus.ACTIVE).count()
    returned = query.filter(Allocation.status == AllocationStatus.RETURNED).count()
    cancelled = query.filter(Allocation.status == AllocationStatus.CANCELLED).count()
    morning = query.filter(Allocation.batch == Batch.MORNING.value).count()
    afternoon = query.filter(Allocation.batch == Batch.AFTERNOON.value).count()
    full_day = query.filter(Allocation.batch == Batch.FULL_DAY.value).count()

    filtered_laptop_ids = [r[0] for r in query.with_entities(Allocation.laptop_id).distinct().all()] if total else []
    filtered_intern_ids = [r[0] for r in query.with_entities(Allocation.intern_id).distinct().all()] if total else []
    unique_laptops_used = len(set(filtered_laptop_ids))
    unique_interns = len(set(filtered_intern_ids))

    total_laptops = db.query(func.count(Laptop.id)).scalar() or 0
    total_interns = db.query(func.count(Intern.id)).scalar() or 0
    free_laptops = db.query(func.count(Laptop.id)).filter(Laptop.status == LaptopStatus.FREE).scalar() or 0

    domain_statics = []
    if domain:
        domain_names = [domain]
    else:
        domain_names = [d.value for d in Domain]
    for dname in domain_names:
        domain_statics.append(DomainStat(
            domain=dname,
            total_allocations=query.filter(Allocation.domain == dname).count(),
            active_allocations=query.filter(Allocation.domain == dname, Allocation.status == AllocationStatus.ACTIVE).count(),
            returned_allocations=query.filter(Allocation.domain == dname, Allocation.status == AllocationStatus.RETURNED).count(),
            cancelled_allocations=query.filter(Allocation.domain == dname, Allocation.status == AllocationStatus.CANCELLED).count(),
        ))

    return ReportsResponse(
        total_allocations=total,
        active_allocations=active,
        returned_allocations=returned,
        cancelled_allocations=cancelled,
        morning_allocations=morning,
        afternoon_allocations=afternoon,
        full_day_allocations=full_day,
        unique_laptops_used=unique_laptops_used,
        unique_interns=unique_interns,
        total_laptops=total_laptops,
        total_interns=total_interns,
        free_laptops=free_laptops,
        domain_stats=domain_statics,
    )


@router.get("/export")
def export_allocations_csv(
    search: Optional[str] = None,
    allocation_date: Optional[date] = None,
    batch: Optional[str] = None,
    domain: Optional[str] = None,
    laptop_number: Optional[str] = None,
    intern_name: Optional[str] = None,
    status: Optional[AllocationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Allocation)
    query = _apply_filters(
        query,
        db,
        allocation_date=allocation_date,
        batch=batch,
        domain=domain,
        laptop_number=laptop_number,
        intern_name=intern_name,
        status=status,
        search=search,
    )
    allocations = query.order_by(Allocation.allocation_date.desc(), Allocation.created_at.desc()).all()

    buffer = StringIO()
    writer = csv_module.writer(buffer)
    writer.writerow([
        "ID", "Laptop", "Intern", "Batch", "Domain",
        "Allocation Date", "Start Time", "End Time", "Status",
    ])
    for a in allocations:
        laptop = db.query(Laptop).filter(Laptop.id == a.laptop_id).first()
        intern = db.query(Intern).filter(Intern.id == a.intern_id).first()
        writer.writerow([
            a.id,
            laptop.laptop_number if laptop else "",
            intern.name if intern else "",
            a.batch,
            a.domain,
            a.allocation_date.isoformat() if a.allocation_date else "",
            a.start_time.strftime("%H:%M") if a.start_time else "",
            a.end_time.strftime("%H:%M") if a.end_time else "",
            a.status.value,
        ])

    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=allocations_export.csv"},
    )


@router.get("/{allocation_id}", response_model=AllocationResponse)
def get_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return _serialize(alloc, db)


@router.post("/", response_model=AllocationResponse, status_code=201)
def create_allocation(
    allocation_data: AllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == allocation_data.laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    intern = db.query(Intern).filter(Intern.id == allocation_data.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    # Real-time double-allocation prevention (transactional)
    active_laptop_allocation = db.query(Allocation).filter(
        Allocation.laptop_id == laptop.id,
        Allocation.status == AllocationStatus.ACTIVE,
    ).first()
    if active_laptop_allocation:
        raise HTTPException(
            status_code=400,
            detail=f"Laptop {laptop.laptop_number} is already allocated.",
        )

    if laptop.status != LaptopStatus.FREE:
        raise HTTPException(
            status_code=400,
            detail=f"Laptop {laptop.laptop_number} is not available for allocation.",
        )

    active_intern_allocation = db.query(Allocation).filter(
        Allocation.intern_id == intern.id,
        Allocation.status == AllocationStatus.ACTIVE,
    ).first()
    if active_intern_allocation:
        raise HTTPException(
            status_code=400,
            detail=f"Intern {intern.name} already has an active laptop allocation.",
        )

    if allocation_data.end_time <= allocation_data.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time.",
        )

    allocation = Allocation(
        laptop_id=laptop.id,
        intern_id=intern.id,
        batch=intern.batch.value,
        domain=intern.domain.value,
        allocation_date=allocation_data.allocation_date,
        start_time=allocation_data.start_time,
        end_time=allocation_data.end_time,
        status=AllocationStatus.ACTIVE,
    )
    try:
        db.add(allocation)
        laptop.status = LaptopStatus.ALLOCATED
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Allocation failed due to a database error.")
    db.refresh(allocation)
    return _serialize(allocation, db)


@router.put("/{allocation_id}/return", response_model=ActionResponse)
def return_laptop(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if allocation.status != AllocationStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active allocations can be returned")

    laptop = db.query(Laptop).filter(Laptop.id == allocation.laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    try:
        allocation.status = AllocationStatus.RETURNED
        allocation.returned_at = datetime.now(timezone.utc)
        laptop.status = LaptopStatus.FREE
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Return failed due to a database error.")

    return ActionResponse(
        allocation_id=allocation.id,
        laptop_number=laptop.laptop_number,
        intern_name="",
        status=allocation.status.value,
        message=f"Laptop {laptop.laptop_number} returned successfully and is now available again.",
    )


@router.put("/{allocation_id}/cancel", response_model=ActionResponse)
def cancel_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if allocation.status != AllocationStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active allocations can be cancelled")

    laptop = db.query(Laptop).filter(Laptop.id == allocation.laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    try:
        allocation.status = AllocationStatus.CANCELLED
        laptop.status = LaptopStatus.FREE
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cancel failed due to a database error.")

    return ActionResponse(
        allocation_id=allocation.id,
        laptop_number=laptop.laptop_number,
        intern_name="",
        status=allocation.status.value,
        message=f"Allocation for {laptop.laptop_number} cancelled successfully.",
    )
