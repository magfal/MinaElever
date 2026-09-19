from datetime import datetime, timezone, timedelta
import os
import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from flask import current_app, request
from sqlalchemy import select
from app.extensions import db

# -------------------------------------------------
# HJÄLPFUNKTIONER
# -------------------------------------------------
def utc_now():
    return datetime.now(timezone.utc)

# Säkerställer att datetime är timezone-aware (UTC)
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Sparar en uppladdad bildfil för en fråga, konverterar den till WebP och returnerar metadata.
def save_image(file):
    if not file or not file.filename:
        return None
    try:
        image = Image.open(file)
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError("Filen är inte en giltig bild.")
    # Öppna bilden igen efter verify()
    file.stream.seek(0)
    image = Image.open(file)
    # Gör om till RGB så att vi kan spara som WebP
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    # Begränsa bildens största dimension
    max_size = 1600
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    # Katalog för frågebilder
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "questions"
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_name = file.filename
    storage_name = f"{uuid.uuid4().hex}.webp"
    filepath = upload_dir / storage_name
    image.save(filepath, "WEBP", quality=82, method=6)
    return {
        "name": original_name,
        "filepath": str(filepath),
        "mime_type": "image/webp",
        "size_bytes": filepath.stat().st_size,
    }