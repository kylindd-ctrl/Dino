from app import db
from datetime import datetime

class SolarResource(db.Model):
    __tablename__ = "solar_resources"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    ghi_kwhm2 = db.Column(db.Float)
    dni_kwhm2 = db.Column(db.Float)
    dhi_kwhm2 = db.Column(db.Float)
    pvspecific_kwh_kwp = db.Column(db.Float)  # FLH-equivalent
    pvtotal_kwh = db.Column(db.Float)
    temperature_c = db.Column(db.Float)
    elevation_m = db.Column(db.Float)

    project = db.relationship("Project", back_populates="solar_resource")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
