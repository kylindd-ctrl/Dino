from app import db
from datetime import datetime

class PVModule(db.Model):
    __tablename__ = "pv_modules"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    brand = db.Column(db.String(255), default="")
    model = db.Column(db.String(255), default="")
    quantity = db.Column(db.Integer, default=0)
    wattage = db.Column(db.Float, default=0)

    project = db.relationship("Project", back_populates="modules")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "brand": self.brand,
            "model": self.model,
            "quantity": self.quantity,
            "wattage": self.wattage,
        }
