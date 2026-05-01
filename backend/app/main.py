from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.data_store import ensure_dataset

app = FastAPI(title="SPECTRUM DYE WORKS - Smart Waste Water Prediction Treatment", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
frontend_dist_dir = frontend_dir / "dist"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
if (frontend_dist_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_dir / "assets")), name="react-assets")


@app.on_event("startup")
def startup_seed_data() -> None:
    ensure_dataset()


@app.get("/")
def root():
    index_file = frontend_dist_dir / "index.html" if (frontend_dist_dir / "index.html").exists() else frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not found. Open /frontend after adding UI files."}

@app.get("/daily_view")
def daily_view():
    dv_file = frontend_dir / "daily_view.html"
    if dv_file.exists():
        return FileResponse(dv_file)
    return {"message": "daily_view.html not found. Make sure you saved it in the frontend folder!"}


docs_dir = Path(__file__).resolve().parents[2] / "docs"
login_bg_file = docs_dir / "gallery_images" / "upscaled_4k.png"


@app.get("/login_bg")
def login_background():
    if login_bg_file.exists():
        return FileResponse(login_bg_file)
    return {"message": "Login background image not found at docs/gallery_images/upscaled_4k.png"}
