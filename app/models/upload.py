from app import db
from datetime import datetime

class Upload(db.Model):
    __tablename__ = "uploads"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    file_type = db.Column(db.String(50))  # opensolar_pdf, gsa_xlsx
    original_filename = db.Column(db.String(255))
    stored_path = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", back_populates="uploads")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_type": self.file_type,
            "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
