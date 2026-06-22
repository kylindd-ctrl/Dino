import re
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath: str) -> str:
    """Extract full text from PDF using pdfplumber."""
    import pdfplumber
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def parse_opensolar_pdf(filepath: str) -> dict:
    """Parse OpenSolar PDF and return structured data."""
    text = extract_text_from_pdf(filepath)

    data = {
        "capacity_kwp": None,
        "annual_generation_kwh": None,
        "co2_reduction_tons": None,
        "system_price_php": None,
        "modules": {"brand": "", "model": "", "quantity": 0, "wattage": 0},
        "inverters": {"brand": "", "model": "", "quantity": 0, "capacity_kw": 0},
    }

    # --- System Capacity ---
    # Pattern 1: "70.560 kW Total Module Power" (most reliable)
    m = re.search(r"([\d.]+)\s*kW\s*Total\s+Module\s+Power", text, re.IGNORECASE)
    if m:
        data["capacity_kwp"] = float(m.group(1))
    else:
        # Pattern 2: number before "kW\nSystem Size"
        m = re.search(r"(\d+\.?\d*)\s*[₱\s].*\n\s*kW\s*\n\s*System Size", text)
        if m:
            data["capacity_kwp"] = float(m.group(1))

    # --- Annual Generation ---
    m = re.search(r"([\d,]+)\s*kWh\s*per\s*year", text, re.IGNORECASE)
    if m:
        data["annual_generation_kwh"] = float(m.group(1).replace(",", ""))

    # --- CO2 Reduction ---
    # Text: "54tons" near "CO₂ reduced per year"
    # Pattern: find "tons" near "reduced" or "CO₂"
    m = re.search(r"(\d+)\s*tons\s", text[:3000], re.IGNORECASE)
    if not m:
        m = re.search(r"(\d+)tons", text[:3000], re.IGNORECASE)
    if m:
        data["co2_reduction_tons"] = float(m.group(1))

    # --- System Price (PHP) ---
    # Pattern: "Total System Price ₱176,400.00" (from quote page, most reliable)
    m = re.search(r"Total\s+System\s+Price\s*₱\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    if m:
        data["system_price_php"] = float(m.group(1).replace(",", ""))
    else:
        # Fallback: net system price
        m = re.search(r"Net\s+System\s+Price\s*₱?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if m:
            data["system_price_php"] = float(m.group(1).replace(",", ""))

    # --- PV Modules ---
    # Pattern: "112 x 630 Watt Panels (JAM66D45-630/LB)"
    m = re.search(
        r"(\d+)\s*x\s+(.+?)\s+(\d+)\s*Watt\s*Panels\s*\(([^)]+)\)",
        text, re.IGNORECASE,
    )
    if m:
        data["modules"]["quantity"] = int(m.group(1))
        data["modules"]["brand"] = m.group(2).strip()
        data["modules"]["wattage"] = float(m.group(3))
        data["modules"]["model"] = m.group(4).strip()
    else:
        # Fallback: look for wattage pattern without "(model)"
        m = re.search(r"(\d+)\s*x\s+(.+?)\s+(\d+)\s*W\w*\s*Panels?", text, re.IGNORECASE)
        if m:
            data["modules"]["quantity"] = int(m.group(1))
            data["modules"]["brand"] = m.group(2).strip()
            data["modules"]["wattage"] = float(m.group(3))
            # Try to extract model from nearby text
            m2 = re.search(r"Panels?\s*\(([^)]+)\)", text[m.end():m.end()+200])
            if m2:
                data["modules"]["model"] = m2.group(1).strip()

    # --- Inverters ---
    # Pattern 1: "1 x S5-GC60K (SOLIS)"
    m = re.search(r"(\d+)\s*x\s+(\S+)\s*\(([^)]+)\)", text)
    if m:
        data["inverters"]["quantity"] = int(m.group(1))
        data["inverters"]["model"] = m.group(2).strip()
        data["inverters"]["brand"] = m.group(3).strip()

    # Inverter capacity: "60 kW Total Inverter Rating"
    m = re.search(r"([\d.]+)\s*kW\s*Total\s+Inverter\s+Rating", text, re.IGNORECASE)
    if m:
        data["inverters"]["capacity_kw"] = float(m.group(1))

    logger.info(
        "PDF parsed: capacity=%.2f kWp, gen=%s kWh/yr, co2=%s t/yr, price=₱%s",
        data["capacity_kwp"] or 0,
        f"{data['annual_generation_kwh']:,.0f}" if data["annual_generation_kwh"] else "?",
        f"{data['co2_reduction_tons']:.0f}" if data["co2_reduction_tons"] else "?",
        f"{data['system_price_php']:,.0f}" if data["system_price_php"] else "?",
    )

    return data
