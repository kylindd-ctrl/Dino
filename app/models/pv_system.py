from app import db
from datetime import datetime

class PVSystem(db.Model):
    __tablename__ = "pv_systems"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    capacity_kwp = db.Column(db.Float)
    annual_generation_kwh = db.Column(db.Float)
    co2_reduction_tons = db.Column(db.Float)
    system_price_php = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", back_populates="pv_system")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "capacity_kwp": self.capacity_kwp,
            "annual_generation_kwh": self.annual_generation_kwh,
            "co2_reduction_tons": self.co2_reduction_tons,
            "system_price_php": self.system_price_php,
        }
