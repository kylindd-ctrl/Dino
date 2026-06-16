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
    from app.models import SolarResource, FinancialResult
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
            pd["solar"] = {"ghi": sr.ghi_kwhm2, "flh": sr.pvspecific_kwh_kwp}
        frs = FinancialResult.query.filter_by(project_id=project.id).all()
        if frs:
            fr = frs[0]
            pd["finance"] = {"capex": fr.total_investment_php, "payback": fr.payback_period_years, "revenue": fr.year1_revenue_php, "irr": fr.irr}
    return render_template("project_detail.html", project_id=project_id, pd=pd)

@main_bp.route("/projects/<int:project_id>/ppt")
def project_ppt(project_id):
    return render_template("project_ppt.html", project_id=project_id)
