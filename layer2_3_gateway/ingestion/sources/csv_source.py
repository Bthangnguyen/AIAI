"""Import POIs from CSV file."""

import csv
from typing import List, Dict
from pathlib import Path


def load_pois_from_csv(filepath: str) -> List[Dict]:
    """Load POI records from CSV.

    Expected columns:
        name, category, latitude, longitude, visit_duration_min,
        price, entrance_fee, open_time, close_time,
        tags (comma-separated), description, is_outdoor
    """
    pois = []
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pois.append({
                "name": row["name"].strip(),
                "category": row["category"].strip(),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "visit_duration_min": int(row.get("visit_duration_min", 60)),
                "price": float(row.get("price", 0)),
                "entrance_fee": float(row.get("entrance_fee", 0)),
                "open_time": int(row.get("open_time", 480)),
                "close_time": int(row.get("close_time", 1260)),
                "tags": [t.strip() for t in row.get("tags", "").split(",") if t.strip()],
                "description": row.get("description", ""),
                "is_outdoor": row.get("is_outdoor", "false").lower() == "true",
            })
    return pois
