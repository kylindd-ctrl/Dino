import logging
from flask import Blueprint, request, jsonify
from app import db
from app.models import Project
from app.services.map_service import parse_google_maps_url, resolve_maps_url

logger = logging.getLogger(__name__)
projects_bp = Blueprint("projects", __name__)

@projects_bp.route("", methods=["GET"])
def list_projects():
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in projects])

@projects_bp.route("", methods=["POST"])
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    name = data.get("name", "").strip()
    customer = data.get("customer_name", "").strip()
    maps_link = data.get("google_maps_link", "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400

    # Parse Google Maps link (now handles redirects)
    geo = parse_google_maps_url(maps_link)

    project = Project(
        name=name,
        customer_name=customer,
        google_maps_link=maps_link,
        latitude=geo["latitude"],
        longitude=geo["longitude"],
        address=geo["address"],
        status="draft",
    )
    db.session.add(project)
    db.session.commit()
    logger.info("Created project %d: %s", project.id, project.name)
    return jsonify(project.to_dict()), 201

@projects_bp.route("/<int:project_id>", methods=["GET"])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = project.to_dict()
    if project.pv_system:
        data["pv_system"] = project.pv_system.to_dict()
    if project.modules:
        data["modules"] = [m.to_dict() for m in project.modules]
    if project.inverters:
        data["inverters"] = [i.to_dict() for i in project.inverters]
    if project.solar_resource:
        data["solar_resource"] = project.solar_resource.to_dict()
    if project.financial_results:
        data["financial_results"] = [r.to_dict() for r in project.financial_results]
    return jsonify(data)

@projects_bp.route("/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    if "name" in data:
        project.name = data["name"]
    if "customer_name" in data:
        project.customer_name = data["customer_name"]
    if "google_maps_link" in data:
        project.google_maps_link = data["google_maps_link"]
        geo = parse_google_maps_url(data["google_maps_link"])
        project.latitude = geo["latitude"]
        project.longitude = geo["longitude"]
        project.address = geo["address"]
    if "status" in data:
        project.status = data["status"]
    db.session.commit()
    return jsonify(project.to_dict())

@projects_bp.route("/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    # Cascade delete all related records (SQLite FK constraint handling)
    from app.models import PVSystem, PVModule, Inverter, SolarResource
    from app.models import MonthlyGeneration, HourlyGeneration, FinancialResult, Upload

    for m in PVModule.query.filter_by(project_id=project.id).all():
        db.session.delete(m)
    for inv in Inverter.query.filter_by(project_id=project.id).all():
        db.session.delete(inv)
    for u in Upload.query.filter_by(project_id=project.id).all():
        db.session.delete(u)
    for fr in FinancialResult.query.filter_by(project_id=project.id).all():
        db.session.delete(fr)
    for mg in MonthlyGeneration.query.filter_by(project_id=project.id).all():
        db.session.delete(mg)
    for hg in HourlyGeneration.query.filter_by(project_id=project.id).all():
        db.session.delete(hg)
    if project.pv_system:
        db.session.delete(project.pv_system)
    if project.solar_resource:
        db.session.delete(project.solar_resource)

    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Deleted"})

# --- New: resolve Google Maps link (handles short URLs) ---
@projects_bp.route("/resolve-link", methods=["POST"])
def resolve_link():
    """Resolve a Google Maps URL (including short links) and return coordinates."""
    data = request.get_json()
    if not data or not data.get("url"):
        return jsonify({"error": "URL required"}), 400

    result = resolve_maps_url(data["url"])
    return jsonify(result)
