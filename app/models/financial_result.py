from app import db
from datetime import datetime

class FinancialResult(db.Model):
    __tablename__ = "financial_results"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    scenario = db.Column(db.String(50))  # self_investment, ppa_20yr, bot_5yr
    total_investment_php = db.Column(db.Float)
    year1_revenue_php = db.Column(db.Float)
    payback_period_years = db.Column(db.Float)
    revenue_5y_php = db.Column(db.Float)
    revenue_20y_php = db.Column(db.Float)
    irr = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", back_populates="financial_results")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
