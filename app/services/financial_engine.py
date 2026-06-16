import logging
import numpy as np

logger = logging.getLogger(__name__)

def run_calculation(project) -> list:
    """Run financial calculations for all scenarios (Phase 4)."""
    # Extract inputs
    pv = project.pv_system
    sr = project.solar_resource
    capacity_kwp = pv.capacity_kwp or 0
    ghi = sr.ghi_kwhm2 or 0
    flh = sr.pvspecific_kwh_kwp or 0
    annual_gen = pv.annual_generation_kwh or (capacity_kwp * flh)

    # Placeholder results - actual logic in Phase 4
    # Values will be computed by replicating cesuan.xlsx formulas
    results = [
        {
            "scenario": "self_investment",
            "total_investment_php": capacity_kwp * 35000,  # placeholder
            "year1_revenue_php": annual_gen * 12,  # placeholder
            "payback_period_years": 3.86,
            "revenue_5y_php": 5165264,
            "revenue_20y_php": 10002704,
            "irr": 0.1089,
        },
    ]
    return results
