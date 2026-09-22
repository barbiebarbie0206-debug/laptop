from fastapi import APIRouter, Depends, HTTPException, Query
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, cast, String
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.laptop import Laptop, LaptopStatus
from ..models.intern import Intern, Batch, Domain
from ..models.allocation import Allocation, AllocationStatus
from ..models.user import User
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

logger = logging.getLogger("laptop_allocation")


class LaptopBase(BaseModel):
    laptop_number: str = Field(..., min_length=1, max_length=20)
    brand: str = Field(..., max_length=50)
    model: str = Field(..., max_length=100)
    serial_number: str = Field(..., max_length=100)
    processor: Optional[str] = Field(None, max_length=100)
    ram: Optional[str] = Field(None, max_length=100)
    storage: Optional[str] = Field(None, max_length=100)
    operating_system: Optional[str] = Field(None, max_length=100)


class LaptopCreate(LaptopBase):
    status: LaptopStatus = LaptopStatus.FREE


class LaptopUpdate(BaseModel):
    laptop_number: Optional[str] = Field(None, min_length=1, max_length=20)
    brand: Optional[str] = Field(None, min_length=1, max_length=50)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    serial_number: Optional[str] = Field(None, min_length=1, max_length=100)
    processor: Optional[str] = Field(None, max_length=100)
    ram: Optional[str] = Field(None, max_length=100)
    storage: Optional[str] = Field(None, max_length=100)
    operating_system: Optional[str] = Field(None, max_length=100)
    status: Optional[LaptopStatus] = None


class LaptopStatusUpdate(BaseModel):
    status: LaptopStatus


class DeactivateResponse(BaseModel):
    id: int
    laptop_number: str
    status: str
    message: str


class InternSummary(BaseModel):
    id: int
    intern_id: str
    name: str
    email: str
    domain: Optional[str] = None
    batch: Optional[str] = None


class LaptopResponse(LaptopBase):
    id: int
    status: LaptopStatus
    created_at: datetime
    updated_at: datetime
    allocation_id: Optional[int] = None
    current_intern: Optional[InternSummary] = None

    model_config = ConfigDict(from_attributes=True)


class LaptopListEnvelope(BaseModel):
    items: List[LaptopResponse]
    total: int = 0
    intern_without_laptop: bool = False


router = APIRouter(prefix="/laptops", tags=["laptops"])


def _serialize_laptop(laptop, current_intern=None, allocation_id=None):
    return {
        "id": laptop.id,
        "laptop_number": laptop.laptop_number,
        "brand": laptop.brand,
        "model": laptop.model,
        "serial_number": laptop.serial_number,
        "processor": laptop.processor,
        "ram": laptop.ram,
        "storage": laptop.storage,
        "operating_system": laptop.operating_system,
        "status": laptop.status.value if isinstance(laptop.status, LaptopStatus) else laptop.status,
        "created_at": laptop.created_at,
        "updated_at": laptop.updated_at,
        "allocation_id": allocation_id,
        "current_intern": (
            {
                "id": current_intern.id,
                "intern_id": current_intern.intern_id,
                "name": current_intern.name,
                "email": current_intern.email,
                "domain": (
                    current_intern.domain.value
                    if isinstance(current_intern.domain, Domain)
                    else current_intern.domain
                ),
                "batch": (
                    current_intern.batch.value
                    if isinstance(current_intern.batch, Batch)
                    else current_intern.batch
                ),
            }
            if current_intern
            else None
        ),
    }


def _domain_matches(term: str):
    needle = term.strip().lower()
    return [d for d in Domain if needle in d.value.lower() or needle in d.name.lower()]


def _batch_matches(term: str):
    needle = term.strip().lower()
    return [b for b in Batch if needle in b.value.lower() or needle in b.name.lower()]


def _matching_interns_query(db: Session, term: str):
    conds = [
        Intern.intern_id.ilike(term),
        Intern.name.ilike(term),
        Intern.email.ilike(term),
        cast(Intern.domain, String).ilike(term),
        cast(Intern.batch, String).ilike(term),
    ]
    domains = _domain_matches(term)
    if domains:
        conds.append(Intern.domain.in_(domains))
    batches = _batch_matches(term)
    if batches:
        conds.append(Intern.batch.in_(batches))
    return db.query(Intern).filter(or_(*conds))


def _search_condition(term: str):
    return or_(
        Laptop.laptop_number.ilike(term),
        Laptop.brand.ilike(term),
        Laptop.model.ilike(term),
        Laptop.serial_number.ilike(term),
        cast(Laptop.status, String).ilike(term),
    )


@router.get("/")
def get_laptops(
    skip: int = 0,
    limit: int = 100,
    status: Optional[LaptopStatus] = None,
    search: Optional[str] = None,
    envelope: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_alloc = and_(
        Allocation.laptop_id == Laptop.id,
        Allocation.status == AllocationStatus.ACTIVE,
    )
    query = (
        db.query(Laptop, Allocation.id, Intern)
        .outerjoin(Allocation, active_alloc)
        .outerjoin(Intern, Allocation.intern_id == Intern.id)
    )
    if status:
        query = query.filter(Laptop.status == status)

    intern_without_laptop = False
    if search:
        term = f"%{search}%"
        laptop_conds = _search_condition(term)
        related_parts = [
            Intern.intern_id.ilike(term),
            Intern.name.ilike(term),
            Intern.email.ilike(term),
            cast(Intern.domain, String).ilike(term),
            cast(Intern.batch, String).ilike(term),
            cast(Allocation.id, String).ilike(term),
            Allocation.batch.ilike(term),
        ]
        domains = _domain_matches(search)
        if domains:
            related_parts.append(Intern.domain.in_(domains))
        batches = _batch_matches(search)
        if batches:
            related_parts.append(Intern.batch.in_(batches))

        query = query.filter(or_(laptop_conds, *related_parts))

        if envelope:
            matched_intern = _matching_interns_query(db, term).first()
            if matched_intern:
                has_active = (
                    db.query(Allocation)
                    .filter(
                        Allocation.intern_id == matched_intern.id,
                        Allocation.status == AllocationStatus.ACTIVE,
                    )
                    .first()
                )
                if not has_active:
                    intern_without_laptop = True

    total = query.distinct().count()
    rows = (
        query.distinct()
        .order_by(Laptop.laptop_number)
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for laptop, allocation_id, intern in rows:
        result.append(_serialize_laptop(laptop, current_intern=intern, allocation_id=allocation_id))

    if envelope:
        return LaptopListEnvelope(
            items=result,
            total=total,
            intern_without_laptop=intern_without_laptop,
        )
    return result


@router.get("/{laptop_id}")
def get_laptop(
    laptop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    allocation = (
        db.query(Allocation)
        .filter(
            Allocation.laptop_id == laptop_id,
            Allocation.status == AllocationStatus.ACTIVE,
        )
        .first()
    )
    intern = db.query(Intern).filter(Intern.id == allocation.intern_id).first() if allocation else None
    return _serialize_laptop(
        laptop,
        current_intern=intern,
        allocation_id=allocation.id if allocation else None,
    )


@router.post("/", response_model=LaptopResponse, status_code=201)
def create_laptop(
    laptop_data: LaptopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop_number = laptop_data.laptop_number.strip().upper()
    serial_number = laptop_data.serial_number.strip().upper()

    if db.query(Laptop).filter(Laptop.laptop_number == laptop_number).first():
        raise HTTPException(status_code=400, detail=f"Laptop number '{laptop_number}' already exists")
    if db.query(Laptop).filter(Laptop.serial_number == serial_number).first():
        raise HTTPException(status_code=400, detail=f"Serial number '{serial_number}' already exists")

    laptop = Laptop(
        laptop_number=laptop_number,
        brand=laptop_data.brand.strip(),
        model=laptop_data.model.strip(),
        serial_number=serial_number,
        processor=laptop_data.processor,
        ram=laptop_data.ram,
        storage=laptop_data.storage,
        operating_system=laptop_data.operating_system,
        status=laptop_data.status,
    )
    db.add(laptop)
    db.commit()
    db.refresh(laptop)
    return laptop


@router.put("/{laptop_id}", response_model=LaptopResponse)
def update_laptop(
    laptop_id: int,
    laptop_data: LaptopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")

    update_data = laptop_data.model_dump(exclude_unset=True)

    new_number = update_data.get("laptop_number")
    if new_number is not None:
        new_number = new_number.strip().upper()
        conflict = db.query(Laptop).filter(
            Laptop.laptop_number == new_number,
            Laptop.id != laptop_id,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail=f"Laptop number '{new_number}' already exists")
        update_data["laptop_number"] = new_number

    new_serial = update_data.get("serial_number")
    if new_serial is not None:
        new_serial = new_serial.strip().upper()
        conflict = db.query(Laptop).filter(
            Laptop.serial_number == new_serial,
            Laptop.id != laptop_id,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail=f"Serial number '{new_serial}' already exists")
        update_data["serial_number"] = new_serial

    for key, value in update_data.items():
        setattr(laptop, key, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data provided")
    db.refresh(laptop)
    return laptop


@router.put("/{laptop_id}/status", response_model=LaptopResponse)
def update_laptop_status(
    laptop_id: int,
    status_data: LaptopStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")
    laptop.status = status_data.status
    db.commit()
    db.refresh(laptop)
    return laptop


@router.put("/{laptop_id}/deactivate", response_model=DeactivateResponse)
def deactivate_laptop(
    laptop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")
    laptop.status = LaptopStatus.INACTIVE
    db.commit()
    db.refresh(laptop)
    return DeactivateResponse(
        id=laptop.id,
        laptop_number=laptop.laptop_number,
        status=laptop.status.value,
        message="Laptop deactivated successfully",
    )


@router.put("/{laptop_id}/activate", response_model=DeactivateResponse)
def activate_laptop(
    laptop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    laptop = db.query(Laptop).filter(Laptop.id == laptop_id).first()
    if not laptop:
        raise HTTPException(status_code=404, detail="Laptop not found")
    laptop.status = LaptopStatus.FREE
    db.commit()
    db.refresh(laptop)
    return DeactivateResponse(
        id=laptop.id,
        laptop_number=laptop.laptop_number,
        status=laptop.status.value,
        message="Laptop activated successfully",
    )
