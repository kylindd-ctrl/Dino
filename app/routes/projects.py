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
    if "roof_area" in data:
        project.roof_area = data["roof_area"]
    if "exchg_date" in data:
        project.exchg_date = data["exchg_date"]
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


# Step 5 financial calculation
@projects_bp.route("/<int:project_id>/step5/calculate", methods=["POST"])
def step5_calculate(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    deg_year1 = float(data.get("deg_year1", 2.0))
    deg_y2plus = float(data.get("deg_y2plus", 0.55))
    inv_type = data.get("investment_type", "self")
    ppa_dp = int(data.get("ppa_discount_pct", 70))
    project.deg_year1 = deg_year1
    project.deg_y2plus = deg_y2plus
    project.investment_type = inv_type
    project.ppa_discount_pct = ppa_dp
    from app.models import MonthlyGeneration, FinancialResult, PVSystem
    monthly = MonthlyGeneration.query.filter_by(project_id=project_id).order_by(MonthlyGeneration.month).all()
    pv = PVSystem.query.filter_by(project_id=project_id).first()
    kwp = pv.capacity_kwp if pv else 0
    annual_gen = pv.annual_generation_kwh if pv else 0
    from app.models import QuoteItem
    quote_items = QuoteItem.query.filter_by(project_id=project_id).all()
    quote_total = sum(i.unit_price * i.quantity for i in quote_items) if quote_items else 0
    total_inv = quote_total if quote_total > 0 else (kwp * 35000 if kwp else 0)
    yearly = []
    cum = 0
    rate = project.electricity_rate or 13.0
    disc = project.revenue_discount or 0.9
    d = [31,28,31,30,31,30,31,31,30,31,30,31]
    md = {m.month: m for m in monthly}
    for y in range(1, 21):
        deg = 1 - (deg_year1 if y == 1 else deg_year1 + deg_y2plus * (y - 1)) / 100
        gen = 0
        for m in range(1, 13):
            mo = md.get(m)
            if mo and mo.pvtotal_kwh:
                gen += mo.pvtotal_kwh
        gen = gen * deg if gen else annual_gen * deg
        rev = gen * rate * disc
        cum += rev
        yearly.append({"year": y, "revenue": round(rev, 2), "cumulative": round(cum, 2)})
    y1rev = yearly[0]["revenue"] if yearly else 0
    scenarios = []
    for dp in [50,55,60,65,70,75,80]:
        t = sum(y["revenue"] * (dp / 100) for y in yearly[:20])
        scenarios.append({"discount_pct": dp, "total_revenue_20y": round(t, 2), "payback_years": round(20 * (total_inv / t) if t else 0, 1), "irr": None})
    FinancialResult.query.filter_by(project_id=project.id, scenario="step5").delete()
    fr = FinancialResult(project_id=project.id, scenario="step5",
        total_investment_php=total_inv, year1_revenue_php=round(y1rev, 2),
        revenue_5y_php=round(sum(y["revenue"] for y in yearly[:5]), 2),
        revenue_20y_php=round(cum, 2),
        payback_period_years=round(total_inv / y1rev, 1) if y1rev else None, irr=None)
    db.session.add(fr)
    project.status = "completed"
    db.session.commit()
    self_inv = {
        "total_investment": total_inv,
        "first_year_revenue": round(y1rev, 2),
        "payback_years": round(total_inv / y1rev, 1) if y1rev else None,
        "irr": None,
        "total_revenue_20y": round(cum, 2),
        "yearly": yearly,
        "simple_roi_pct": round((cum - total_inv) / total_inv * 100, 1) if total_inv else 0
    }
    selected = None
    for s in scenarios:
        if s["discount_pct"] == ppa_dp:
            selected = s
            selected["first_year_revenue"] = round(y1rev * ppa_dp / 100, 2)
            break
    return jsonify({
        "self_investment": self_inv,
        "selected_scenario": selected,
        "all_scenarios": scenarios,
        "investment_type": inv_type,
        "ppa_discount_pct": ppa_dp
    })
@projects_bp.route("/<int:project_id>/step5", methods=["GET"])
def step5_get_config(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify({"deg_year1": getattr(project, "deg_year1", 2.0),
        "deg_y2plus": getattr(project, "deg_y2plus", 0.55),
        "investment_type": getattr(project, "investment_type", "self"),
        "ppa_discount_pct": getattr(project, "ppa_discount_pct", 70)})

# --- New: resolve Google Maps link (handles short URLs) ---
@projects_bp.route("/resolve-link", methods=["POST"])
def resolve_link():
    """Resolve a Google Maps URL (including short links) and return coordinates."""
    data = request.get_json()
    if not data or not data.get("url"):
        return jsonify({"error": "URL required"}), 400

    result = resolve_maps_url(data["url"])
    return jsonify(result)
