from app import db
from datetime import datetime

class PriceLibrary(db.Model):
    __tablename__ = "price_library"
    id = db.Column(db.Integer, primary_key=True)
    equipment_name = db.Column(db.String(255), nullable=False)
    model = db.Column(db.String(255), default="")
    unit_price = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default="pcs")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "equipment_name": self.equipment_name, "model": self.model,
                "unit_price": self.unit_price, "unit": self.unit or "pcs"}
