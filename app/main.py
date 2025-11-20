from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import uploads, products, webhooks

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Product Importer")

# Use absolute paths so there is no confusion
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# API routers
app.include_router(uploads.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


# HTML pages
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    return templates.TemplateResponse("products.html", {"request": request})


@app.get("/webhooks", response_class=HTMLResponse)
async def webhooks_page(request: Request):
    return templates.TemplateResponse("webhooks.html", {"request": request})
