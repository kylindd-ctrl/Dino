import os
import logging
from flask import render_template, jsonify, current_app
from app.routes import main_bp

logger = logging.getLogger(__name__)

import urllib.parse

LOG_FILE = r"C:\Users\admin\Desktop\MAPS_DEBUG.txt"

@main_bp.route("/api/debug/log")
def debug_log():
    from flask import request
    from datetime import datetime
    msg = request.args.get("msg", "")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    return "", 204

@main_bp.route("/")
def index():
    """Dashboard / project list page."""
    return render_template("index.html")

@main_bp.route("/projects/new")
def new_project():
    return render_template("project_form.html")

@main_bp.route("/projects/<int:project_id>")
def project_detail(project_id):
    from app.models import Project, PVSystem, PVModule, Inverter
    from app.models import SolarResource, FinancialResult, MonthlyGeneration
    project = Project.query.get(project_id)
    pd = None
    if project:
        pd = {
            "id": project.id,
            "name": project.name,
            "customer_name": project.customer_name,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "address": project.address,
            "google_maps_link": project.google_maps_link,
            "status": project.status,
        }
        pv = project.pv_system
        if pv:
            pd["pv_system"] = {
                "capacity_kwp": pv.capacity_kwp,
                "annual_generation_kwh": pv.annual_generation_kwh,
                "co2_reduction_tons": pv.co2_reduction_tons,
            }
        modules = PVModule.query.filter_by(project_id=project.id).all()
        if modules:
            m = modules[0]
            pd["module"] = {"quantity": m.quantity, "brand": m.brand, "model": m.model, "wattage": m.wattage}
        invs = Inverter.query.filter_by(project_id=project.id).all()
        if invs:
            i = invs[0]
            pd["inverter"] = {"quantity": i.quantity, "brand": i.brand, "model": i.model, "capacity_kw": i.capacity_kw}
        sr = project.solar_resource
        if sr:
            pd["solar"] = {"ghi": sr.ghi_kwhm2}
        mg = MonthlyGeneration.query.filter_by(project_id=project.id).order_by(MonthlyGeneration.month).all()
        if mg:
            d=[31,28,31,30,31,30,31,31,30,31,30,31]
            pd["monthly"] = [{"m": m.month, "v": round(m.pvtotal_kwh/d[m.month-1], 1) if m.pvtotal_kwh else 0} for m in mg]
        frs = FinancialResult.query.filter_by(project_id=project.id).all()
        if frs:
            fr = frs[0]
            pd["finance"] = {"capex": fr.total_investment_php, "payback": fr.payback_period_years, "revenue": fr.year1_revenue_php, "irr": fr.irr}
    # Load quote data for template
    try:
        from app.models import PriceLibrary, QuoteItem
        lib = [l.to_dict() for l in PriceLibrary.query.order_by(PriceLibrary.equipment_name).all()]
        qitems = [i.to_dict() for i in QuoteItem.query.filter_by(project_id=project_id).order_by(QuoteItem.id).all()]
        totals = {"cost": sum(i["total_cost"] for i in qitems), "price": sum(i["total_price"] for i in qitems), "php_total": round(sum(i["unit_price"] * (1 + (i.get("gross_margin", 0) or 0)/100) * i["quantity"] for i in qitems) * (project.exchange_rate or 8.76))}
    except:
        lib, qitems, totals = [], [], {"cost": 0, "price": 0, "php_total": 0}
    return render_template("project_detail.html", project_id=project_id, pd=pd, items=qitems, lib=lib, totals=totals)

@main_bp.route("/projects/<int:project_id>/ppt")
def project_ppt(project_id):
    return render_template("project_ppt.html", project_id=project_id)
