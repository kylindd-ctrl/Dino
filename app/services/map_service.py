import os
import re
import urllib.parse
import requests

def _follow_redirect(url: str) -> str:
    """Follow HTTP redirects to resolve shortened URLs like goo.gl."""
    if not url:
        return url
    # Only follow redirects for known shortener domains
    shorteners = ("goo.gl", "bit.ly", "tinyurl.com", "maps.app.goo.gl")
    if any(d in url.lower() for d in shorteners):
        try:
            resp = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SolarProposal/1.0)"},
            )
            return resp.url
        except Exception:
            pass
    return url


def _extract_coords(text: str) -> tuple:
    """Extract (lat, lng) from any text using multiple patterns."""
    # Pattern 1: @lat,lng
    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 2: ?q=lat,lng
    m = re.search(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 3: ?ll=lat,lng
    m = re.search(r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 4: /search/lat,+lng  or  /search/lat,lng
    m = re.search(r"/search/(-?\d+\.\d+),\+?(-?\d+\.\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 5: /maps/place/.../@lat,lng
    m = re.search(r"/@(-?\d+\.\d+),(-?\d+\.\d+),?\d*z", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 6: /?center=lat,lng
    m = re.search(r"center=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Pattern 7: bare lat,lng numbers in URL (last resort)
    nums = re.findall(r"(-?\d+\.\d+)", text)
    if len(nums) >= 2:
        # Validate they look like lat/lng
        lat = float(nums[0])
        lng = float(nums[1])
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return (lat, lng)

    return (None, None)


def parse_google_maps_url(url: str) -> dict:
    """Parse Google Maps URL to extract lat, lng, and address."""
    result = {"latitude": None, "longitude": None, "address": ""}
    if not url:
        return result

    # Follow redirects for short URLs
    resolved_url = _follow_redirect(url)

    # Extract coordinates from the (possibly resolved) URL
    lat, lng = _extract_coords(resolved_url)
    result["latitude"] = lat
    result["longitude"] = lng

    # Reverse geocode via Nominatim if coordinates found
    if lat and lng:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "json",
                    "accept-language": "en",
                },
                headers={"User-Agent": "SolarProposalPlatform/1.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                result["address"] = data.get("display_name", "")
        except Exception:
            pass

    return result


def resolve_maps_url(url: str) -> dict:
    """Resolve a Maps URL and return coordinates + address. Used by frontend API."""
    result = {"latitude": None, "longitude": None, "address": "", "resolved_url": url}
    if not url:
        return result

    resolved_url = _follow_redirect(url)
    result["resolved_url"] = resolved_url

    lat, lng = _extract_coords(resolved_url)
    result["latitude"] = lat
    result["longitude"] = lng

    if lat and lng:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json", "accept-language": "en"},
                headers={"User-Agent": "SolarProposalPlatform/1.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                result["address"] = data.get("display_name", "")
        except Exception:
            pass
    return result
