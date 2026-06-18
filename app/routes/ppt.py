import logging
from flask import Blueprint, send_file, jsonify, current_app, request
from app import db
from app.models import Project
import os

logger = logging.getLogger(__name__)
ppt_bp = Blueprint("ppt", __name__)



@ppt_bp.route("/api/projects/<int:project_id>/scan-ppt-placeholders", methods=["GET"])
def scan_ppt_placeholders(project_id):
    """Scan uploaded PPT template and return found placeholders."""
    from app.models import Upload
    import re
    from pptx import Presentation
    
    uploaded = Upload.query.filter_by(project_id=project_id, file_type="ppt_template").first()
    if not uploaded or not os.path.exists(uploaded.stored_path):
        return jsonify({"error": "No PPT template uploaded. Upload a template first."}), 400
    
    prs = Presentation(uploaded.stored_path)
    placeholders = set()
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    found = re.findall(r'\{\{[^}]+\}\}', para.text)
                    for ph in found:
                        placeholders.add(ph)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        found = re.findall(r'\{\{[^}]+\}\}', cell.text)
                        for ph in found:
                            placeholders.add(ph)
    
    # Build known mappings
    known_fields = {
        "{{capacity}}": "System Capacity (kWp)", "{{flh}}": "Full Load Hours",
        "{{inv_count}}": "Inverter Count", "{{module_count}}": "Module Count",
        "{{total_investment}}": "Total Investment (PHP)", "{{year1_revenue}}": "First Year Revenue (PHP)",
        "{{payback_period}}": "Payback Period (Years)", "{{rev_20y}}": "20-Year Revenue (PHP)",
        "{{irr_20y}}": "20-Year IRR", "{{rev_5y}}": "5-Year Revenue (PHP)", "{{irr_5y}}": "5-Year IRR",
        "{{inv_power}}": "Inverter Power (kW)", "{{carbon_reduction}}": "CO2 Reduction (tons)",
        "{{pro_own}}": "Customer Name", "{{adr}}": "Address", "{{geographic}}": "Coordinates (DMS)",
        "{{ghi}}": "GHI (kWh/m²)", "{{roof_area}}": "Roof Area (m²)", "{{Exchg}}": "Exchange Rate",
        "{{Exchg_date}}": "Exchange Rate Date", "{{set}}": "Inverter Unit"
    };
    
    result = []
    for ph in sorted(placeholders):
        clean = ph.replace("{", "").replace("}", "").strip()
        field = known_fields.get(ph, "")
        result.append({
            "placeholder": ph,
            "field": field,
            "matched": bool(field),
            "value": ""
        })
    
    return jsonify({"placeholders": result, "count": len(result)}), 200

@ppt_bp.route("/api/projects/<int:project_id>/upload-ppt-template", methods=["POST"])
def upload_ppt_template(project_id):
    """Upload a PPT template for placeholder replacement."""
    from werkzeug.utils import secure_filename
    from app import db
    from app.models import Upload
    
    project = Project.query.get_or_404(project_id)
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename.endswith('.pptx'):
        return jsonify({"error": "Only .pptx files allowed"}), 400
    
    # Delete old PPT template uploads
    for u in Upload.query.filter_by(project_id=project.id, file_type="ppt_template").all():
        db.session.delete(u)
    
    # Save new template
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(project.id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = "ppt_template.pptx"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    record = Upload(project_id=project.id, file_type="ppt_template",
                    original_filename=file.filename, stored_path=filepath)
    db.session.add(record)
    db.session.commit()
    
    return jsonify({"message": "PPT template uploaded", "path": filepath}), 200

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
