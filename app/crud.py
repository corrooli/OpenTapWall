"""CRUD operations for Beer entities.

Each function expects a SQLModel Session (FastAPI dependency supplies it).
Errors are surfaced via HTTPException for straightforward API integration.
"""

from typing import Optional, Sequence

from sqlmodel import Session, select
from fastapi import HTTPException, status

from .models import Beer, BeerCreate, BeerUpdate


def get_beers(*, session: Session, skip: int = 0, limit: int = 100) -> Sequence[Beer]:
    """Return beers ordered by tap number with optional pagination."""
    stmt = select(Beer).order_by(Beer.tap_number).offset(skip).limit(limit)
    return session.exec(stmt).all()


def get_beer(*, session: Session, beer_id: int) -> Optional[Beer]:
    """Fetch a single beer by id or raise 404 if absent."""
    beer = session.get(Beer, beer_id)
    if not beer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Beer {beer_id} not found"
        )
    return beer


def create_beer(*, session: Session, beer_in: BeerCreate) -> Beer:
    """Persist a new beer record from a validated create schema."""
    beer = Beer(**beer_in.model_dump())
    session.add(beer)
    session.commit()
    session.refresh(beer)
    return beer


def update_beer(*, session: Session, beer_id: int, beer_in: BeerUpdate) -> Beer:
    """Apply a partial update (PATCH semantics) to a beer and return it."""
    beer = get_beer(session=session, beer_id=beer_id)
    beer_data = beer_in.model_dump(exclude_unset=True)
    for key, value in beer_data.items():
        setattr(beer, key, value)
    session.add(beer)
    session.commit()
    session.refresh(beer)
    return beer


def delete_beer(*, session: Session, beer_id: int) -> None:
    """Delete a beer by id (idempotent: raises 404 if not found)."""
    beer = get_beer(session=session, beer_id=beer_id)
    session.delete(beer)
    session.commit()
