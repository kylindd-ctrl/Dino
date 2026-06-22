from app import db
from datetime import datetime

class TariffLibrary(db.Model):
    __tablename__ = 'tariff_library'
    id = db.Column(db.Integer, primary_key=True)
    rate_name = db.Column(db.String(255), nullable=False)
    rate_value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), default='PHP/kWh')
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'rate_name': self.rate_name, 'rate_value': self.rate_value,
                'unit': self.unit or 'PHP/kWh', 'description': self.description or ''}

