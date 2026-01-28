from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Base(SQLModel):
    """Base class with common audit fields"""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={
                                           "onupdate": datetime.utcnow})
