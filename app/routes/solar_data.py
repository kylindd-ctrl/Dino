import os
import logging
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import (
    Project, Upload, SolarResource,
    MonthlyGeneration, HourlyGeneration, FinancialResult,
)
from app.services.gsa_parser import parse_gsa_excel
from app.utils.file_storage import save_upload

logger = logging.getLogger(__name__)
solar_data_bp = Blueprint("solar_data", __name__)


@solar_data_bp.route("/api/projects/<int:project_id>/upload/gsa", methods=["POST"])
def upload_gsa(project_id):
    project = Project.query.get_or_404(project_id)
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]

    try:
        filepath = save_upload(file, project_id, "gsa", current_app.config["UPLOAD_FOLDER"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        gsa_data = parse_gsa_excel(filepath)
    except Exception as e:
        logger.exception("GSA parse failed")
        return jsonify({"error": f"Failed to parse GSA file: {str(e)}"}), 422

    # --- Clear old GSA data ---
    for u in Upload.query.filter_by(project_id=project.id, file_type="gsa_xlsx").all():
        db.session.delete(u)

    if project.solar_resource:
        db.session.delete(project.solar_resource)
        project.solar_resource = None

    for m in MonthlyGeneration.query.filter_by(project_id=project.id).all():
        db.session.delete(m)
    for h in HourlyGeneration.query.filter_by(project_id=project.id).all():
        db.session.delete(h)

    for fr in FinancialResult.query.filter_by(project_id=project.id).all():
        db.session.delete(fr)

    # --- Save new GSA data ---
    map_data = gsa_data["map_data"]
    coords = gsa_data["coords"]
    sr = SolarResource(project_id=project.id)
    sr.latitude = coords["lat"]
    sr.longitude = coords["lng"]
    sr.ghi_kwhm2 = map_data.get("GHI")
    sr.dni_kwhm2 = map_data.get("DNI")
    sr.dhi_kwhm2 = map_data.get("DIF")
    sr.pvspecific_kwh_kwp = map_data.get("PVOUT_specific")
    sr.temperature_c = map_data.get("TEMP")
    sr.elevation_m = map_data.get("ELE")
    db.session.add(sr)

    for m in gsa_data["monthly"]:
        db.session.add(MonthlyGeneration(project_id=project.id, **m))
    for h in gsa_data["hourly"]:
        db.session.add(HourlyGeneration(project_id=project.id, **h))

    upload_record = Upload(
        project_id=project.id,
        file_type="gsa_xlsx",
        original_filename=file.filename,
        stored_path=filepath,
    )
    db.session.add(upload_record)

    project.status = "gsa_uploaded"
    db.session.commit()

    logger.info("Project %d: GSA replaced, old data cleared", project_id)
    return jsonify({"message": "GSA data processed"}), 200


@solar_data_bp.route("/api/projects/<int:project_id>/solar-resource", methods=["GET"])
def get_solar_resource(project_id):
    sr = SolarResource.query.filter_by(project_id=project_id).first()
    if not sr:
        return jsonify({"error": "No solar resource data"}), 404
    return jsonify(sr.to_dict())


@solar_data_bp.route("/api/projects/<int:project_id>/monthly-generation", methods=["GET"])
def get_monthly_generation(project_id):
    rows = MonthlyGeneration.query.filter_by(project_id=project_id).order_by(MonthlyGeneration.month).all()
    return jsonify([r.to_dict() for r in rows])


@solar_data_bp.route("/api/projects/<int:project_id>/hourly-generation", methods=["GET"])
def get_hourly_generation(project_id):
    rows = HourlyGeneration.query.filter_by(project_id=project_id).order_by(
        HourlyGeneration.month, HourlyGeneration.hour_start
    ).all()
    return jsonify([r.to_dict() for r in rows])
