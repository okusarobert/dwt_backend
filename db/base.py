from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base

# The declarative base that all models will inherit from.
Base = declarative_base()

class Timestamped(Base):
    """
    An abstract base class that provides self-updating
    `created_at` and `updated_at` columns.
    """
    __abstract__ = True
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
