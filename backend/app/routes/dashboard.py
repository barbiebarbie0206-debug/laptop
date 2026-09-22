from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional
from collections import defaultdict
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.allocation import Allocation, AllocationStatus
from ..models.laptop import Laptop, LaptopStatus
from ..models.intern import Intern, Batch, Domain
from ..models.user import User
from pydantic import BaseModel
from datetime import date


class LaptopStatusItem(BaseModel):
    name: str
    value: int


class BatchAllocationItem(BaseModel):
    name: str
    value: int


class DomainAllocationItem(BaseModel):
    name: str
    value: int


class AllocationTrendItem(BaseModel):
    month: str
    allocated: int
    returned: int


class DashboardStats(BaseModel):
    total_laptops: int
    free_laptops: int
    allocated_laptops: int
    maintenance_laptops: int
    inactive_laptops: int
    total_interns: int
    active_allocations: int
    returned_allocations: int
    morning_allocations: int
    afternoon_allocations: int
    full_day_allocations: int
    laptop_status_distribution: List[LaptopStatusItem]
    batch_allocations: List[BatchAllocationItem]
    domain_allocations: List[DomainAllocationItem]
    allocation_trend: List[AllocationTrendItem]


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Total Laptops = current inventory only, i.e. rows with a current valid
    # status. INACTIVE/retired records are excluded from the inventory total
    # (they remain reportable via their own stat, not inflated into the total).
    _CURRENT_INVENTORY_STATUSES = (
        LaptopStatus.FREE,
        LaptopStatus.ALLOCATED,
        LaptopStatus.MAINTENANCE,
    )
    status_counts = {
        status: db.query(func.count(Laptop.id)).filter(Laptop.status == status).scalar() or 0
        for status in _CURRENT_INVENTORY_STATUSES
    }
    free_laptops = status_counts[LaptopStatus.FREE]
    allocated_laptops = status_counts[LaptopStatus.ALLOCATED]
    maintenance_laptops = status_counts[LaptopStatus.MAINTENANCE]
    inactive_laptops = db.query(func.count(Laptop.id)).filter(Laptop.status == LaptopStatus.INACTIVE).scalar() or 0
    total_laptops = free_laptops + allocated_laptops + maintenance_laptops

    total_interns = db.query(func.count(Intern.id)).scalar() or 0
    active_allocations = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.status == AllocationStatus.ACTIVE)
        .scalar() or 0
    )
    returned_allocations = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.status == AllocationStatus.RETURNED)
        .scalar() or 0
    )

    morning_allocations = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.batch == Batch.MORNING.value)
        .scalar() or 0
    )
    afternoon_allocations = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.batch == Batch.AFTERNOON.value)
        .scalar() or 0
    )
    full_day_allocations = (
        db.query(func.count(Allocation.id))
        .filter(Allocation.batch == Batch.FULL_DAY.value)
        .scalar() or 0
    )

    laptop_status_distribution = [
        LaptopStatusItem(name="Free", value=free_laptops),
        LaptopStatusItem(name="Allocated", value=allocated_laptops),
        LaptopStatusItem(name="Maintenance", value=maintenance_laptops),
    ]

    batch_allocations = [
        BatchAllocationItem(name="Morning", value=morning_allocations),
        BatchAllocationItem(name="Afternoon", value=afternoon_allocations),
        BatchAllocationItem(name="Full Day", value=full_day_allocations),
    ]

    domain_rows = (
        db.query(Allocation.domain, func.count(Allocation.id))
        .group_by(Allocation.domain)
        .order_by(func.count(Allocation.id).desc())
        .all()
    )
    domain_allocations = [
        DomainAllocationItem(name=r[0] if r[0] else "Unknown", value=r[1]) for r in domain_rows
    ]

    allocation_trend = _monthly_trend(db)

    return DashboardStats(
        total_laptops=total_laptops,
        free_laptops=free_laptops,
        allocated_laptops=allocated_laptops,
        maintenance_laptops=maintenance_laptops,
        inactive_laptops=inactive_laptops,
        total_interns=total_interns,
        active_allocations=active_allocations,
        returned_allocations=returned_allocations,
        morning_allocations=morning_allocations,
        afternoon_allocations=afternoon_allocations,
        full_day_allocations=full_day_allocations,
        laptop_status_distribution=laptop_status_distribution,
        batch_allocations=batch_allocations,
        domain_allocations=domain_allocations,
        allocation_trend=allocation_trend,
    )


def _monthly_trend(db: Session) -> List[AllocationTrendItem]:
    """Real monthly 'allocated vs returned' totals from the allocations table."""
    totals: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for row in db.query(Allocation).all():
        if row.allocation_date:
            key = row.allocation_date.strftime("%Y-%m")
            totals[key][0] += 1
        if row.returned_at and row.status == AllocationStatus.RETURNED:
            key = row.returned_at.strftime("%Y-%m")
            totals[key][1] += 1

    months = sorted(totals.keys())[-12:]
    return [
        AllocationTrendItem(
            month=key,
            allocated=totals[key][0],
            returned=totals[key][1],
        )
        for key in months
    ]
