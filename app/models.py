"""Data models and Pydantic / SQLModel schemas for the OpenTapWall application.

The module defines:
  * Beer / BeerBase / BeerCreate / BeerUpdate – core beer tap entities
  * DisplaySettings (+ update schema) – single row of wall display metadata
  * StoredImage – generic BLOB storage for beer images and the logo

Images are stored exclusively as BLOBs via the ``StoredImage`` table.
"""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class BeerBase(SQLModel):
    """Shared attributes for Beer variants (non-table base).

    Includes optional numeric stats. ``tap_number`` and ``name`` are required.
    """

    tap_number: int
    name: str
    style: Optional[str] = None
    abv: Optional[float] = None
    og: Optional[float] = None
    sg: Optional[float] = None
    ibu: Optional[int] = None
    ebc: Optional[int] = None


class Beer(BeerBase, table=True):
    """Persisted beer record with optional link to a stored image.

    ``image_id`` points to a ``StoredImage`` row (kind="beer").
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    image_id: Optional[int] = Field(default=None, foreign_key="storedimage.id")


class BeerCreate(BeerBase):
    """Schema for creating a new beer; all BeerBase fields required."""

class BeerUpdate(SQLModel):
    """Partial update schema; all fields optional to enable PATCH semantics."""

    tap_number: Optional[int] = None
    name: Optional[str] = None
    style: Optional[str] = None
    abv: Optional[float] = None
    og: Optional[float] = None
    sg: Optional[float] = None
    ibu: Optional[int] = None
    ebc: Optional[int] = None


class DisplaySettings(SQLModel, table=True):
    """Singleton table holding wall display customizations.

    Row id is fixed at 1. ``logo_image_id`` references a ``StoredImage`` row
    (kind="logo").
    """

    id: int = Field(default=1, primary_key=True)
    title: str = Field(default="What’s on Tap")
    logo_image_id: Optional[int] = Field(default=None, foreign_key="storedimage.id")


class DisplaySettingsUpdate(SQLModel):
    """PATCH payload for updating display settings (currently only title)."""

    title: Optional[str] = None


class StoredImage(SQLModel, table=True):
    """Generic binary image storage.

    ``kind`` distinguishes functional usage (e.g. "beer" or "logo"). ``ref_id``
    links back to a Beer when ``kind='beer'``; unused for logos.
    ``data`` holds raw image bytes; ``content_type`` preserves the MIME type.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str
    ref_id: Optional[int] = None
    content_type: str
    data: bytes
    created_at: datetime = Field(default_factory=datetime.utcnow)
