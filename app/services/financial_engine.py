import logging
import math

logger = logging.getLogger(__name__)

def irr(cashflows, guess=0.1, max_iter=1000, tolerance=1e-7):
    """Calculate IRR using Newton's method."""
    rate = guess
    for _ in range(max_iter):
        npv = 0
        dnpv = 0  # derivative of NPV
        for i, cf in enumerate(cashflows):
            try:
                denominator = (1 + rate) ** i
                npv += cf / denominator
                dnpv += -i * cf / (denominator * (1 + rate))
            except (OverflowError, ZeroDivisionError):
                return None
        if abs(dnpv) < tolerance:
            return None
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tolerance:
            return new_rate
        rate = new_rate
    return rate if rate > -1 else None

def project_cashflow(total_investment, first_year_revenue, years=20,
                     deg_year1=2.0, deg_y2plus=0.55, discount_ratio=1.0):
    """Generate yearly cashflow array with degradation.
    Revenue degradation applies FROM Year 1 TO Year 2 (deg_year1),
    then Year 2 onwards using deg_y2plus.
    """
    cf = [-total_investment]
    revenue = first_year_revenue
    yearly_revenues = []
    for y in range(1, years + 1):
        annual_cf = revenue * discount_ratio
        cf.append(annual_cf)
        yearly_revenues.append({
            "year": y,
            "revenue": round(annual_cf, 2),
            "net_cashflow": round(sum(cf), 2),
        })
        # Apply degradation for NEXT year's revenue
        degradation = (deg_year1 / 100.0) if y == 1 else (deg_y2plus / 100.0)
        revenue = revenue * (1 - degradation)
    return cf, yearly_revenues

def payback_period(cashflows):
    """Calculate payback period in years."""
    cumulative = 0
    for i, cf in enumerate(cashflows):
        cumulative += cf
        if cumulative >= 0 and i > 0:
            prev_cum = cumulative - cf
            fraction = -prev_cum / cf if cf != 0 else 0
            return round((i - 1) + fraction, 2)
    return None

def calculate_self_investment(total_investment, first_year_revenue,
                              deg_year1, deg_y2plus, years=20):
    """Calculate Self Investment scenario."""
    cf, yearly = project_cashflow(total_investment, first_year_revenue,
                                  years, deg_year1, deg_y2plus, 1.0)
    irr_val = irr(cf)
    payback = payback_period(cf)
    total_revenue = sum(cf[1:])
    simple_roi = ((total_revenue - total_investment) / total_investment * 100) if total_investment else 0
    return {
        "type": "self_investment",
        "total_investment": round(total_investment, 2),
        "first_year_revenue": round(first_year_revenue, 2),
        "payback_years": payback,
        "simple_roi_pct": round(simple_roi, 2),
        "irr": round(irr_val, 6) if irr_val else None,
        "total_revenue_20y": round(total_revenue, 2),
        "yearly": yearly,
    }

def calculate_ppa_scenario(total_investment, first_year_revenue,
                           deg_year1, deg_y2plus, discount_pct, years=20):
    """Calculate PPA scenario for a specific discount percentage."""
    discount_ratio = discount_pct / 100.0
    cf, yearly = project_cashflow(total_investment, first_year_revenue,
                                  years, deg_year1, deg_y2plus, discount_ratio)
    irr_val = irr(cf)
    payback = payback_period(cf)
    total_revenue = sum(cf[1:])
    return {
        "discount_pct": discount_pct,
        "discount_ratio": discount_ratio,
        "total_investment": round(total_investment, 2),
        "first_year_revenue": round(first_year_revenue, 2),
        "third_party_investment": round(total_investment, 2),
        "customer_investment": 0,
        "operating_years": years,
        "payback_years": payback,
        "total_revenue_20y": round(total_revenue, 2),
        "irr": round(irr_val, 6) if irr_val else None,
        "yearly_cashflow": round(sum(cf), 2),
        "yearly": yearly,
    }

def calculate_all_ppa_scenarios(total_investment, first_year_revenue,
                                deg_year1, deg_y2plus):
    """Calculate all PPA discount scenarios (50% to 80%)."""
    preset_discounts = [50, 55, 60, 65, 70, 75, 80]
    scenarios = []
    for dp in preset_discounts:
        s = calculate_ppa_scenario(total_investment, first_year_revenue,
                                   deg_year1, deg_y2plus, dp)
        scenarios.append(s)
    return scenarios

def run_step5(params):
    """Main entry point for Step 5 calculations.
    params: {
        total_investment, first_year_revenue,
        deg_year1, deg_y2plus,
        investment_type: "self" or "ppa",
        ppa_discount_pct (optional, for single scenario)
    }
    """
    ti = params.get("total_investment", 0)
    fyr = params.get("first_year_revenue", 0)
    d1 = params.get("deg_year1", 2.0)
    d2 = params.get("deg_y2plus", 0.55)
    inv_type = params.get("investment_type", "self")

    result = {
        "total_investment": round(ti, 2),
        "first_year_revenue": round(fyr, 2),
        "deg_year1": d1,
        "deg_y2plus": d2,
        "investment_type": inv_type,
    }

    if inv_type == "self":
        result["self_investment"] = calculate_self_investment(ti, fyr, d1, d2)
    else:
        target_dp = params.get("ppa_discount_pct", 70)
        result["ppa_discount_pct"] = target_dp
        # Always calculate all preset scenarios for the table
        result["all_scenarios"] = calculate_all_ppa_scenarios(ti, fyr, d1, d2)
        # Directly calculate the selected scenario (supports any discount value)
        result["selected_scenario"] = calculate_ppa_scenario(ti, fyr, d1, d2, target_dp, years=20)
        # Ensure selected_scenario has proper fields
        result["selected_scenario"]["is_preset"] = target_dp in [50, 55, 60, 65, 70, 75, 80]

    return result
