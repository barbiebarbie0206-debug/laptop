from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.intern import Intern, Batch, Domain
from ..models.allocation import Allocation, AllocationStatus
from ..models.user import User
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime


class InternCreate(BaseModel):
    intern_id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=15)
    batch: Batch
    domain: Domain


class InternUpdate(BaseModel):
    intern_id: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=7, max_length=15)
    batch: Optional[Batch] = None
    domain: Optional[Domain] = None


class InternResponse(InternCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    id: int
    intern_id: str
    message: str


class BatchSummary(BaseModel):
    morning: int
    afternoon: int
    full_day: int
    total: int


router = APIRouter(prefix="/interns", tags=["interns"])


@router.get("/", response_model=List[InternResponse])
def get_interns(
    skip: int = 0,
    limit: int = 100,
    batch: Optional[Batch] = None,
    domain: Optional[Domain] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Intern)
    if batch:
        query = query.filter(Intern.batch == batch)
    if domain:
        query = query.filter(Intern.domain == domain)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Intern.intern_id.ilike(term)) |
            (Intern.name.ilike(term)) |
            (Intern.email.ilike(term)) |
            (Intern.phone.ilike(term))
        )
    return query.order_by(Intern.intern_id).offset(skip).limit(limit).all()


@router.get("/summary", response_model=BatchSummary)
def get_batch_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts = {
        batch: db.query(func.count(Intern.id)).filter(Intern.batch == batch).scalar() or 0
        for batch in Batch
    }
    return BatchSummary(
        morning=counts[Batch.MORNING],
        afternoon=counts[Batch.AFTERNOON],
        full_day=counts[Batch.FULL_DAY],
        total=sum(counts.values()),
    )


@router.get("/{intern_id}", response_model=InternResponse)
def get_intern(
    intern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intern = db.query(Intern).filter(Intern.id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    return intern


@router.post("/", response_model=InternResponse, status_code=201)
def create_intern(
    intern_data: InternCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intern_id = intern_data.intern_id.strip().upper()
    email = intern_data.email.strip().lower()

    if db.query(Intern).filter(Intern.intern_id == intern_id).first():
        raise HTTPException(status_code=400, detail=f"Intern ID '{intern_id}' already exists")
    if db.query(Intern).filter(Intern.email == email).first():
        raise HTTPException(status_code=400, detail=f"Email '{email}' already exists")

    intern = Intern(
        intern_id=intern_id,
        name=intern_data.name.strip(),
        email=email,
        phone=intern_data.phone.strip(),
        batch=intern_data.batch,
        domain=intern_data.domain,
    )
    db.add(intern)
    db.commit()
    db.refresh(intern)
    return intern


@router.put("/{intern_id_row}", response_model=InternResponse)
def update_intern(
    intern_id_row: int,
    intern_data: InternUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intern = db.query(Intern).filter(Intern.id == intern_id_row).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    update_data = intern_data.model_dump(exclude_unset=True)

    new_id = update_data.get("intern_id")
    if new_id is not None:
        new_id = new_id.strip().upper()
        conflict = db.query(Intern).filter(
            Intern.intern_id == new_id,
            Intern.id != intern_id_row,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail=f"Intern ID '{new_id}' already exists")
        update_data["intern_id"] = new_id

    new_email = update_data.get("email")
    if new_email is not None:
        new_email = new_email.strip().lower()
        conflict = db.query(Intern).filter(
            Intern.email == new_email,
            Intern.id != intern_id_row,
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail=f"Email '{new_email}' already exists")
        update_data["email"] = new_email

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "phone" in update_data and update_data["phone"]:
        update_data["phone"] = update_data["phone"].strip()

    for key, value in update_data.items():
        setattr(intern, key, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data provided")
    db.refresh(intern)
    return intern


@router.delete("/{intern_id_row}", response_model=DeleteResponse)
def delete_intern(
    intern_id_row: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intern = db.query(Intern).filter(Intern.id == intern_id_row).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    active_allocations = db.query(Allocation).filter(
        Allocation.intern_id == intern_id_row,
        Allocation.status == AllocationStatus.ACTIVE,
    ).first()
    if active_allocations:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete intern with active allocations. Complete allocations first.",
        )

    db.delete(intern)
    db.commit()
    return DeleteResponse(id=intern_id_row, intern_id=intern.intern_id, message="Intern deleted successfully")
