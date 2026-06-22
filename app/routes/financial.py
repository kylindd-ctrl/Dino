import logging
from flask import Blueprint, request, jsonify
from app import db
from app.models import Project, FinancialResult, QuoteItem, MonthlyGeneration
from app.services.financial_engine import run_step5

logger = logging.getLogger(__name__)
financial_bp = Blueprint("financial", __name__)

@financial_bp.route("/api/projects/<int:project_id>/step5", methods=["GET"])
def get_step5_data(project_id):
    """Get current Step 5 data (config + calculation)."""
    project = Project.query.get_or_404(project_id)

    # Build config from stored values
    config = {
        "deg_year1": getattr(project, "deg_year1", 2.0) or 2.0,
        "deg_y2plus": getattr(project, "deg_y2plus", 0.55) or 0.55,
        "investment_type": getattr(project, "investment_type", "self") or "self",
        "ppa_discount_pct": getattr(project, "ppa_discount_pct", 70) or 70,
    }
    return jsonify(config)

@financial_bp.route("/api/projects/<int:project_id>/step5", methods=["POST"])
def save_step5_config(project_id):
    """Save Step 5 configuration."""
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    for attr in ["deg_year1", "deg_y2plus", "investment_type", "ppa_discount_pct"]:
        if attr in data:
            setattr(project, attr, data[attr])
    db.session.commit()
    return jsonify({"ok": True})

@financial_bp.route("/api/projects/<int:project_id>/step5/calculate", methods=["POST"])
def calculate_step5(project_id):
    """Run Step 5 financial calculations."""
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}

    # Get Total Investment from PHP Quotation
    items = QuoteItem.query.filter_by(project_id=project_id).all()
    if not items:
        return jsonify({"error": "No quotation data. Add equipment in Step 4 first."}), 400
    exchange_rate = project.exchange_rate or 8.76
    total_investment = sum(
        i.unit_price / (1 - (i.gross_margin or 0) / 100) * i.quantity * exchange_rate
        for i in items
    )

    # Get First Year Revenue from Step 4 Revenue Calculation
    mg = MonthlyGeneration.query.filter_by(project_id=project_id).all()
    # Single source of truth: use saved total_revenue_php from Revenue Calculation
    if project.total_revenue_php and project.total_revenue_php > 0:
        first_year_revenue = project.total_revenue_php
    elif mg:
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        first_year_revenue = 0
        for m in mg:
            dg = m.daily_gen_kwh or 0
            if dg == 0 and m.pvtotal_kwh and m.pvtotal_kwh > 0:
                dg = m.pvtotal_kwh / days_in_month[m.month - 1]
            wd = m.working_days or days_in_month[m.month - 1]
            monthly_gen = dg * wd
            monthly_rev = monthly_gen * (project.electricity_rate or 13)
            first_year_revenue += monthly_rev
        first_year_revenue *= (project.revenue_discount or 1.0)
    else:
        first_year_revenue = project.total_revenue_php or 0

    # Get config from request or stored values
    deg1 = data.get("deg_year1", getattr(project, "deg_year1", 2.0) or 2.0)
    deg2 = data.get("deg_y2plus", getattr(project, "deg_y2plus", 0.55) or 0.55)
    inv_type = data.get("investment_type", getattr(project, "investment_type", "self") or "self")
    ppa_dp = data.get("ppa_discount_pct", getattr(project, "ppa_discount_pct", 70) or 70)

    # Save config
    project.deg_year1 = deg1
    project.deg_y2plus = deg2
    project.investment_type = inv_type
    project.ppa_discount_pct = ppa_dp
    db.session.commit()

    # Run calculation
    params = {
        "total_investment": total_investment,
        "first_year_revenue": first_year_revenue,
        "deg_year1": deg1,
        "deg_y2plus": deg2,
        "investment_type": inv_type,
        "ppa_discount_pct": ppa_dp,
    }
    result = run_step5(params)

    # Save to FinancialResult for persistence
    FinancialResult.query.filter_by(project_id=project_id, scenario="step5").delete()
    import json
    fr = FinancialResult(
        project_id=project_id,
        scenario="step5",
        total_investment_php=round(total_investment, 2),
        year1_revenue_php=round(first_year_revenue, 2),
    )
    # Store the full result as JSON
    fr.step5_result_json = json.dumps(result)
    db.session.add(fr)
    db.session.commit()

    return jsonify(result), 200
