from app import db
from datetime import datetime

class QuoteItem(db.Model):
    __tablename__ = "quote_items"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    equipment_name = db.Column(db.String(255), nullable=False)
    model = db.Column(db.String(255), default="")
    unit_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=1)
    gross_margin = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default="pcs")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", back_populates="quote_items")

    def total_cost(self):
        return round(self.unit_price * self.quantity, 2)

    def total_price(self):
        """Calculate sell price with gross margin.
        gross_margin: stored as percentage (e.g. 30 = 30%).
        Supports both raw percentage (30) and decimal (0.3).
        Price = cost / (1 - margin_decimal)
        """
        margin = self.gross_margin
        if margin is None or margin <= 0:
            return self.total_cost()
        # Normalize to decimal
        if margin > 1:
            margin = margin / 100.0
        if margin <= 0 or margin >= 1:
            return self.total_cost()
        return round(self.total_cost() / (1 - margin), 2)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id,
                "equipment_name": self.equipment_name, "model": self.model,
                "unit_price": self.unit_price, "quantity": self.quantity,
                "gross_margin": self.gross_margin, "unit": self.unit or "pcs",
                "total_cost": self.total_cost(), "total_price": self.total_price()}
