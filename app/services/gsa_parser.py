import pandas as pd
def _sf(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(",", "").replace(" ", ""))
    except: return None
def _sf(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(',', '').replace(' ', ''))
    except: return None
import logging

logger = logging.getLogger(__name__)

def parse_gsa_excel(filepath: str) -> dict:
    """Parse GSA Excel workbook and return structured data."""

    xls = pd.ExcelFile(filepath, engine="openpyxl")

    # --- Map_data sheet ---
    df_map = pd.read_excel(xls, sheet_name="Map_data", header=None)
    map_data = {}
    for _, row in df_map.iterrows():
        key = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        val = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else None
        if key and val is not None:
            map_data[key] = _sf(val) if _sf(val) is not None else str(val)

    # --- Site_info sheet ---
    df_site = pd.read_excel(xls, sheet_name="Site_info", header=None)
    site_info = {}
    for _, row in df_site.iterrows():
        key = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        val = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else ""
        if key:
            site_info[key] = str(val).strip()

    # --- Monthly_averages sheet ---
    df_monthly = pd.read_excel(xls, sheet_name="Monthly_averages", header=None)
    # Find header row
    header_idx = None
    for idx, row in df_monthly.iterrows():
        vals = [str(v).strip() for v in row if pd.notna(v)]
        if "PVOUT_specific" in vals:
            header_idx = idx
            break
    if header_idx is not None:
        df_monthly.columns = df_monthly.iloc[header_idx]
        df_monthly = df_monthly.iloc[header_idx + 1 :].reset_index(drop=True)
    else:
        df_monthly = None

    # --- Hourly_profiles sheet ---
    df_hourly = pd.read_excel(xls, sheet_name="Hourly_profiles", header=None)
    # Find the "Total photovoltaic power output" section
    hourly_start = None
    for idx, row in df_hourly.iterrows():
        vals = [str(v).strip() for v in row if pd.notna(v)]
        if "Total photovoltaic power output" in " ".join(vals):
            hourly_start = idx + 2  # Skip description + blank rows
            break

    hourly_data = []
    if hourly_start is not None:
        df_power = df_hourly.iloc[hourly_start:].reset_index(drop=True)
        # Rows: hour label + 12 month columns
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for _, row in df_power.iterrows():
            label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            if label.lower() == "sum":
                break
            if not label or " - " not in label:
                continue
            hour_start = int(label.split(" - ")[0])
            for mi, m in enumerate(months):
                val = row.iloc[mi + 1] if mi + 1 < len(row) else None
                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                    hourly_data.append({
                        "month": mi + 1,
                        "hour_start": hour_start,
                        "power_output_wh": float(val),
                    })

    # Coordinates from Overview or Site_info
    coords = {"lat": None, "lng": None}
    coord_text = site_info.get("Geographical coordinates", "")
    if coord_text:
        import re
        m = re.search(r"(-?\d+\.\d+)°.*?(-?\d+\.\d+)°", coord_text)
        if m:
            coords["lat"] = float(m.group(1))
            coords["lng"] = float(m.group(2))

    # Build PV config
    df_pv = pd.read_excel(xls, sheet_name="PV_config", header=None)
    pv_config = {}
    for _, row in df_pv.iterrows():
        key = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        val = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None
        if "System size" in key.lower() and val is not None:
            pv_config["system_size_kwp"] = float(val)

    # Monthly data
    monthly_list = []
    if df_monthly is not None:
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        for _, row in df_monthly.iterrows():
            m_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            if m_name in month_names:
                monthly_list.append({
                    "month": month_names.index(m_name) + 1,
                    "pvspecific_kwh_kwp": _sf(row.iloc[1]) if pd.notna(row.iloc[1]) else 0,
                    "pvtotal_kwh": _sf(row.iloc[2]) if pd.notna(row.iloc[2]) else 0,
                    "dni_kwhm2": _sf(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else 0,
                })

    return {
        "coords": coords,
        "site_info": site_info,
        "map_data": map_data,
        "pv_config": pv_config,
        "monthly": monthly_list,
        "hourly": hourly_data,
    }
