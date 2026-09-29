import os
import shutil
from pathlib import Path


def get_data_root() -> Path:
    """Return the shared persistent data directory for PDFs, vectors, and cache."""
    project_data = Path(__file__).resolve().parents[1] / "data"
    configured_mount = os.getenv("RENDER_DISK_PATH")
    if configured_mount:
        return Path(configured_mount)

    default_mount = Path("/opt/render/project/data")
    if default_mount.exists():
        return default_mount
    return project_data


def get_pdf_directory() -> Path:
    """Return the PDF directory and migrate PDFs from the old app-local path."""
    project_data = Path(__file__).resolve().parents[1] / "data"
    data_root = get_data_root()
    pdf_directory = data_root / "pdf"
    pdf_directory.mkdir(parents=True, exist_ok=True)

    legacy_directory = project_data / "pdf"
    if data_root != project_data and legacy_directory.exists():
        for source in legacy_directory.iterdir():
            destination = pdf_directory / source.name
            if source.is_file() and source.suffix.lower() == ".pdf" and not destination.exists():
                shutil.copy2(source, destination)

    return pdf_directory
