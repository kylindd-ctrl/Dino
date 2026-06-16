from app import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    google_maps_link = db.Column(db.Text, default="")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    address = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pv_system = db.relationship("PVSystem", uselist=False, back_populates="project")
    modules = db.relationship("PVModule", back_populates="project")
    inverters = db.relationship("Inverter", back_populates="project")
    solar_resource = db.relationship("SolarResource", uselist=False, back_populates="project")
    monthly_generation = db.relationship("MonthlyGeneration", back_populates="project")
    hourly_generation = db.relationship("HourlyGeneration", back_populates="project")
    financial_results = db.relationship("FinancialResult", back_populates="project")
    uploads = db.relationship("Upload", back_populates="project")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "customer_name": self.customer_name,
            "google_maps_link": self.google_maps_link,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Project {self.id}: {self.name}>"
