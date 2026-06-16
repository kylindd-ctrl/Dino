import logging
from flask import Blueprint, send_file, jsonify, current_app, request
from app import db
from app.models import Project
import os

logger = logging.getLogger(__name__)
ppt_bp = Blueprint("ppt", __name__)

@ppt_bp.route("/api/projects/<int:project_id>/generate-ppt", methods=["POST"])
def generate_ppt(project_id):
    project = Project.query.get_or_404(project_id)

    # Delegate to PPT generator (stub - Phase 5)
    from app.services.ppt_generator import generate_proposal
    output_path = generate_proposal(project, current_app.config)

    project.status = "completed"
    db.session.commit()

    return jsonify({
        "message": "PPT generated",
        "download_url": f"/api/projects/{project_id}/download-ppt",
    }), 200

@ppt_bp.route("/api/projects/<int:project_id>/download-ppt", methods=["GET"])
def download_ppt(project_id):
    project = Project.query.get_or_404(project_id)
    output_dir = current_app.config["OUTPUT_FOLDER"]
    filename = f"{project.name}_proposal.pptx".replace(" ", "_")
    filepath = os.path.join(output_dir, str(project_id), filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "PPT not yet generated"}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)
