import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Date, Time, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base, engine


class AllocationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    laptop_id = Column(Integer, ForeignKey("laptops.id"), nullable=False)
    intern_id = Column(Integer, ForeignKey("interns.id"), nullable=False)
    batch = Column(String(20), nullable=False)
    domain = Column(String(50), nullable=False)
    allocation_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(AllocationStatus), default=AllocationStatus.ACTIVE, nullable=False)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    laptop = relationship("Laptop", back_populates="allocations")
    intern = relationship("Intern", back_populates="allocations")


# Database-level guard: a laptop can only ever have ONE ACTIVE allocation at a time,
# even under concurrent requests (the API also validates this before inserting).
index_dialect = engine.dialect.name
if index_dialect == "mysql":
    # MySQL has no partial/filtered indexes. A faithful equivalent is provided by
    # the generated-column unique key in scripts/mysql_dataset.sql; the API-level
    # double-allocation check remains the runtime guard here.
    uq_allocations_active_laptop = None
else:
    uq_allocations_active_laptop = Index(
        "uq_allocations_active_laptop",
        Allocation.laptop_id,
        unique=True,
        sqlite_where=text("status = 'ACTIVE'"),
        postgresql_where=text("status = 'ACTIVE'"),
    )
