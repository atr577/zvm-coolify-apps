"""
Pagination schemas for list endpoints.
"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper.

    Example:
        {
            "items": [...],
            "total": 100,
            "page": 1,
            "limit": 20,
            "pages": 5
        }
    """
    items: List[T]
    total: int
    page: int
    limit: int

    @property
    def pages(self) -> int:
        """Total number of pages."""
        if self.limit == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit

    class Config:
        # Allow computed properties in response
        from_attributes = True
