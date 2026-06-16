import logging
from flask import Blueprint, jsonify
from app import db
from app.models import Project, FinancialResult

logger = logging.getLogger(__name__)
financial_bp = Blueprint("financial", __name__)

@financial_bp.route("/api/projects/<int:project_id>/calculate", methods=["POST"])
def calculate(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.pv_system:
        return jsonify({"error": "No PV system data. Upload OpenSolar PDF first."}), 400
    if not project.solar_resource:
        return jsonify({"error": "No solar resource data. Upload GSA file first."}), 400

    # Delegate to financial engine (stub - Phase 4)
    from app.services.financial_engine import run_calculation
    results = run_calculation(project)

    # Save results
    FinancialResult.query.filter_by(project_id=project.id).delete()
    for scenario_data in results:
        fr = FinancialResult(project_id=project.id, **scenario_data)
        db.session.add(fr)

    project.status = "calculated"
    db.session.commit()
    return jsonify({"message": "Calculation complete", "results": results}), 200

@financial_bp.route("/api/projects/<int:project_id>/financial-results", methods=["GET"])
def get_results(project_id):
    results = FinancialResult.query.filter_by(project_id=project_id).all()
    return jsonify([r.to_dict() for r in results])
