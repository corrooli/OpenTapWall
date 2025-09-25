"""FastAPI application entrypoint: routes, templates, and startup logic."""

from fastapi import FastAPI, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select, Session

from .db import get_session, engine
from .models import Beer, DisplaySettings, DisplaySettingsUpdate, StoredImage
from .routers.beers import router as beers_router

app = FastAPI(title="OpenTap")
app.include_router(beers_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def seed_data():
    """Insert a few sample beers if database starts empty.

    Provides an immediate visual when the wall is first launched.
    """
    with Session(engine) as session:
        existing = session.exec(select(Beer).limit(1)).first()
        if not existing:
            session.add_all([
                Beer(tap_number=1, name="Pale Ale", style="APA", abv=5.2, ibu=35, ebc=12),
                Beer(tap_number=2, name="Stout", style="Dry Stout", abv=4.5, ibu=40, ebc=80),
                Beer(tap_number=3, name="IPA", style="West Coast IPA", abv=6.5, ibu=60, ebc=18),
            ])
            session.commit()


@app.get("/", response_class=HTMLResponse)
def wall(request: Request, session=Depends(get_session)):
    """Render the public tap wall display."""
    beers = session.exec(select(Beer).order_by(Beer.tap_number)).all()
    settings = session.get(DisplaySettings, 1)
    return templates.TemplateResponse("index.html", {"request": request, "beers": beers, "settings": settings})


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, session=Depends(get_session)):
    """Render the administration interface for managing beers and settings."""
    settings = session.get(DisplaySettings, 1)
    return templates.TemplateResponse("admin.html", {"request": request, "settings": settings})


@app.patch("/settings", response_model=DisplaySettings)
def update_settings(payload: DisplaySettingsUpdate, session=Depends(get_session)):
    """Update display settings (currently title only)."""
    settings = session.get(DisplaySettings, 1)
    if not settings:
        settings = DisplaySettings()
        session.add(settings)
        session.flush()
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(settings, k, v)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


@app.post("/settings/logo", response_model=DisplaySettings)
def upload_logo(file: UploadFile = File(...), session=Depends(get_session)):
    """Upload and persist a logo image (stored as BLOB)."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    data = file.file.read()
    if len(data) > 1_000_000:
        raise HTTPException(status_code=413, detail="Logo too large (max 1MB)")
    settings = session.get(DisplaySettings, 1) or DisplaySettings()
    img = StoredImage(kind="logo", ref_id=None, content_type=file.content_type, data=data)
    session.add(img)
    session.flush()
    settings.logo_image_id = img.id
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


@app.get("/images/{image_id}")
def get_image(image_id: int, session=Depends(get_session)):
    """Serve a stored image by id with basic caching headers."""
    img = session.get(StoredImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=img.data, media_type=img.content_type, headers=headers)
