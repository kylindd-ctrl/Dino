import os
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models import Project, Upload, PVSystem, PVModule, Inverter, FinancialResult
from app.services.pdf_parser import parse_opensolar_pdf
from app.utils.file_storage import save_upload

logger = logging.getLogger(__name__)
uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.route("/api/projects/<int:project_id>/upload/pdf", methods=["POST"])
def upload_pdf(project_id):
    project = Project.query.get_or_404(project_id)
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]

    try:
        filepath = save_upload(file, project_id, "pdf", current_app.config["UPLOAD_FOLDER"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Parse PDF
    try:
        pdf_data = parse_opensolar_pdf(filepath)
    except Exception as e:
        logger.exception("PDF parse failed")
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 422

    # --- Clear old data before saving new ---
    # Old upload records
    for u in Upload.query.filter_by(project_id=project.id, file_type="opensolar_pdf").all():
        db.session.delete(u)

    # Old modules & inverters
    for m in PVModule.query.filter_by(project_id=project.id).all():
        db.session.delete(m)
    for inv in Inverter.query.filter_by(project_id=project.id).all():
        db.session.delete(inv)

    # Old financial results (data changed)
    for fr in FinancialResult.query.filter_by(project_id=project.id).all():
        db.session.delete(fr)

    # Old PV system
    if project.pv_system:
        db.session.delete(project.pv_system)
        project.pv_system = None

    # --- Save new data ---
    pv = PVSystem(project_id=project.id, **{
        k: v for k, v in pdf_data.items()
        if k not in ("modules", "inverters") and v is not None
    })
    db.session.add(pv)

    if pdf_data["modules"]["quantity"] > 0:
        db.session.add(PVModule(project_id=project.id, **pdf_data["modules"]))

    if pdf_data["inverters"]["quantity"] > 0:
        db.session.add(Inverter(project_id=project.id, **pdf_data["inverters"]))

    upload_record = Upload(
        project_id=project.id,
        file_type="opensolar_pdf",
        original_filename=file.filename,
        stored_path=filepath,
    )
    db.session.add(upload_record)

    project.status = "pdf_uploaded"
    db.session.commit()

    logger.info("Project %d: PDF replaced, old data cleared", project_id)
    return jsonify({"message": "PDF processed", "data": pdf_data}), 200


@uploads_bp.route("/api/projects/<int:project_id>/uploads", methods=["GET"])
def list_uploads(project_id):
    Project.query.get_or_404(project_id)
    uploads = Upload.query.filter_by(project_id=project_id).all()
    return jsonify([u.to_dict() for u in uploads])
