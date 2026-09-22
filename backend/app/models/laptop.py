import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class LaptopStatus(str, enum.Enum):
    FREE = "FREE"
    ALLOCATED = "ALLOCATED"
    RETURNED = "RETURNED"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class Laptop(Base):
    __tablename__ = "laptops"

    id = Column(Integer, primary_key=True, index=True)
    laptop_number = Column(String(20), unique=True, nullable=False, index=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    processor = Column(String(100), nullable=True)
    ram = Column(String(100), nullable=True)
    storage = Column(String(100), nullable=True)
    operating_system = Column(String(100), nullable=True)
    status = Column(Enum(LaptopStatus), default=LaptopStatus.FREE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    allocations = relationship("Allocation", back_populates="laptop")
