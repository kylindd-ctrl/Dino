from app import db

class MonthlyGeneration(db.Model):
    __tablename__ = "monthly_generation"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    month = db.Column(db.Integer)
    pvspecific_kwh_kwp = db.Column(db.Float)
    pvtotal_kwh = db.Column(db.Float)
    dni_kwhm2 = db.Column(db.Float)

    project = db.relationship("Project", back_populates="monthly_generation")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class HourlyGeneration(db.Model):
    __tablename__ = "hourly_generation"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    month = db.Column(db.Integer)
    hour_start = db.Column(db.Integer)
    power_output_wh = db.Column(db.Float)
    dni_whm2 = db.Column(db.Float)

    project = db.relationship("Project", back_populates="hourly_generation")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
