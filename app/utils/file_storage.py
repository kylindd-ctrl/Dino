import os
from werkzeug.utils import secure_filename

ALLOWED_PDF = {"pdf"}
ALLOWED_XLSX = {"xlsx"}

def save_upload(file, project_id: int, file_type: str, base_folder: str) -> str:
    """Save uploaded file to project folder. Returns the stored path."""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_type == "pdf" and ext not in ALLOWED_PDF:
        raise ValueError("Only PDF files are allowed for OpenSolar uploads.")
    if file_type == "gsa" and ext not in ALLOWED_XLSX:
        raise ValueError("Only .xlsx files are allowed for GSA uploads.")

    project_dir = os.path.join(base_folder, str(project_id))
    os.makedirs(project_dir, exist_ok=True)
    filename = f"{file_type}_{secure_filename(file.filename)}"
    filepath = os.path.join(project_dir, filename)
    file.save(filepath)
    return filepath
