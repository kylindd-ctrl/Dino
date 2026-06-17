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
    exchange_rate = db.Column(db.Float, nullable=True)
    electricity_rate = db.Column(db.Float, nullable=True)
    revenue_discount = db.Column(db.Float, nullable=True)
    total_revenue_php = db.Column(db.Float, nullable=True)
    total_investment_php = db.Column(db.Float, nullable=True)
    deg_year1 = db.Column(db.Float, nullable=True)
    deg_y2plus = db.Column(db.Float, nullable=True)
    investment_type = db.Column(db.String(20), nullable=True)
    ppa_discount_pct = db.Column(db.Integer, nullable=True)
    roof_area = db.Column(db.Float, nullable=True)
    exchg_date = db.Column(db.String(50), nullable=True)
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
    quote_items = db.relationship("QuoteItem", back_populates="project")

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
            "exchange_rate": self.exchange_rate,
            "electricity_rate": self.electricity_rate,
            "roof_area": self.roof_area,
            "exchg_date": self.exchg_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Project {self.id}: {self.name}>"
