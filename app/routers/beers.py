"""Beer API router: CRUD endpoints and image upload handler."""

import os

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel import Session

from ..db import get_session
from .. import crud, models

router = APIRouter(prefix="/beers", tags=["beers"])


@router.get("/", response_model=list[models.Beer])
def list_beers(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    """List beers ordered by tap number with pagination."""
    return crud.get_beers(session=session, skip=skip, limit=limit)


@router.get("/{beer_id}", response_model=models.Beer)
def read_beer(beer_id: int, session: Session = Depends(get_session)):
    """Retrieve a single beer or raise 404."""
    return crud.get_beer(session=session, beer_id=beer_id)


@router.post("/", response_model=models.Beer, status_code=201)
def add_beer(beer_in: models.BeerCreate, session: Session = Depends(get_session)):
    """Create a new beer via JSON payload."""
    return crud.create_beer(session=session, beer_in=beer_in)


@router.patch("/{beer_id}", response_model=models.Beer)
def edit_beer(
    beer_id: int, beer_in: models.BeerUpdate, session: Session = Depends(get_session)
):
    """Patch (partial update) an existing beer."""
    return crud.update_beer(session=session, beer_id=beer_id, beer_in=beer_in)


@router.delete("/{beer_id}", status_code=204)
def remove_beer(beer_id: int, session: Session = Depends(get_session)):
    """Delete a beer by id."""
    crud.delete_beer(session=session, beer_id=beer_id)


IMAGES_DIR = os.getenv("IMAGES_DIR", "/data/images")
os.makedirs(IMAGES_DIR, exist_ok=True)


@router.post("/upload-image/{beer_id}", response_model=models.Beer)
def upload_image(
    beer_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)
):
    """Attach an uploaded image to a beer (stored as BLOB).

    Enforces a 1MB size cap; legacy filesystem images remain accessible if
    still referenced.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    data = file.file.read()
    if len(data) > 1_000_000:
        raise HTTPException(status_code=413, detail="Image too large (max 1MB)")
    beer = crud.get_beer(session=session, beer_id=beer_id)
    img = models.StoredImage(
        kind="beer", ref_id=beer.id, content_type=file.content_type, data=data
    )
    session.add(img)
    session.flush()
    beer.image_id = img.id
    session.add(beer)
    session.commit()
    session.refresh(beer)
    return beer


@router.post("/create", response_model=models.Beer)
def create_beer_form(
    tap_number: int = Form(...),
    name: str = Form(...),
    style: str | None = Form(None),
    abv: str | None = Form(None),
    ibu: str | None = Form(None),
    ebc: str | None = Form(None),
    session: Session = Depends(get_session),
):
    """Admin form-based creation endpoint.

    Coerces numeric inputs; invalid numeric strings are treated as null.
    """

    def fnum(val, cast):
        if val in (None, ""):
            return None
        try:
            return cast(val)
        except ValueError:
            return None

    beer_in = models.BeerCreate(
        tap_number=tap_number,
        name=name,
        style=style or None,
        abv=fnum(abv, float),
        ibu=fnum(ibu, int),
        ebc=fnum(ebc, int),
    )
    return crud.create_beer(session=session, beer_in=beer_in)
