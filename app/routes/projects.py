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

    # === TOTAL INVESTMENT = sum of quote items (PHP) ===
    from app.models import QuoteItem
    quote_items = QuoteItem.query.filter_by(project_id=project_id).all()
    # total_price() already handles gross_margin, gives sell price
    total_inv = round(sum(i.total_price() for i in quote_items) * (project.exchange_rate or 8.76)) if quote_items else 0

    # === FIRST YEAR REVENUE from saved revenue data ===
    # Use the saved total_revenue_php on the project if available
    first_year_rev = project.total_revenue_php or 0

    # === MONTHLY GENERATION from GSA ===
    monthly = MonthlyGeneration.query.filter_by(project_id=project_id).order_by(MonthlyGeneration.month).all()
    pv = PVSystem.query.filter_by(project_id=project_id).first()
    kwp = pv.capacity_kwp if pv else 0
    annual_gen = pv.annual_generation_kwh if pv else 0

    # Build base first-year revenue (pre-degradation) from GSA monthly data
    rate = project.electricity_rate or 13.0
    disc = project.revenue_discount or 0.9
    md = {m.month: m for m in monthly}
    has_monthly = len(monthly) > 0
    if has_monthly:
        base_gen = sum(mo.pvtotal_kwh for mo in monthly if mo and mo.pvtotal_kwh)
        base_y1_revenue = base_gen * rate * disc
    elif annual_gen:
        base_y1_revenue = annual_gen * rate * disc
    else:
        base_y1_revenue = first_year_rev

    # Apply degradation: Y1 = deg_year1%, Y2+ = deg_y2plus/year compounded
    y1_factor = 1 - deg_year1 / 100
    y2plus_factor = 1 - deg_y2plus / 100
    yearly = []
    cum = 0
    for y in range(1, 21):
        if y == 1:
            factor = y1_factor
        else:
            factor = y1_factor * (y2plus_factor ** (y - 1))
        rev = base_y1_revenue * factor
        cum += rev
        yearly.append({"year": y, "revenue": round(rev, 2), "cumulative": round(cum, 2)})

    first_year_rev = yearly[0]["revenue"]

    y1rev = yearly[0]["revenue"] if yearly else 0

    # Calculate IRR using Newton's method
    if total_inv > 0 and len(yearly) > 0:
        def npv(rate):
            return sum(y["revenue"] / ((1 + rate) ** y["year"]) for y in yearly) - total_inv
        guess = 0.1
        for _ in range(100):
            f = npv(guess)
            f_prime = sum(-y["year"] * y["revenue"] / ((1 + guess) ** (y["year"] + 1)) for y in yearly)
            if abs(f_prime) < 1e-10:
                break
            new_guess = guess - f / f_prime
            if abs(new_guess - guess) < 1e-6:
                guess = new_guess
                break
            guess = new_guess
        irr_value = round(guess, 6) if 0 < guess < 5 else None
    else:
        irr_value = None

    # Generate PPA scenarios
    scenarios = []
    for dp in [50, 55, 60, 65, 70, 75, 80]:
        t = sum(y["revenue"] * (dp / 100) for y in yearly[:20])
        payback = round(20 * (total_inv / t), 1) if t and total_inv else None
        ppa_irr = round(((t / total_inv) ** (1/20) - 1), 6) if t > 0 and total_inv > 0 else None
        scenarios.append({"discount_pct": dp, "total_investment": total_inv, "total_revenue_20y": round(t, 2), "payback_years": payback, "irr": ppa_irr})

    # Save FinancialResult for PPT export
    FinancialResult.query.filter_by(project_id=project.id, scenario="step5").delete()
    fr = FinancialResult(
        project_id=project.id, scenario="step5",
        total_investment_php=total_inv,
        year1_revenue_php=round(y1rev, 2),
        revenue_5y_php=round(sum(y["revenue"] for y in yearly[:5]), 2),
        revenue_20y_php=round(cum, 2),
        payback_period_years=round(total_inv / y1rev, 1) if y1rev else None,
        irr=irr_value
    )
    db.session.add(fr)
    if total_inv > 0:
        project.status = "completed"
    db.session.commit()

    self_inv = {
        "total_investment": total_inv,
        "first_year_revenue": round(y1rev, 2),
        "payback_years": round(total_inv / y1rev, 1) if y1rev else None,
        "irr": irr_value,
        "total_revenue_20y": round(cum, 2),
        "yearly": yearly,
        "simple_roi_pct": round((cum - total_inv) / total_inv * 100, 1) if total_inv else 0
    }
    selected = None
    for s in scenarios:
        if s["discount_pct"] == ppa_dp:
            selected = s
            selected["first_year_revenue"] = round(first_year_rev * ppa_dp / 100, 2)
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
    return jsonify({
        "deg_year1": getattr(project, "deg_year1", 2.0),
        "deg_y2plus": getattr(project, "deg_y2plus", 0.55),
        "investment_type": getattr(project, "investment_type", "self"),
        "ppa_discount_pct": getattr(project, "ppa_discount_pct", 70)
    })

@projects_bp.route("/resolve-link", methods=["POST"])
def resolve_link():
    data = request.get_json()
    if not data or not data.get("url"):
        return jsonify({"error": "URL required"}), 400
    result = resolve_maps_url(data["url"])
    return jsonify(result)
