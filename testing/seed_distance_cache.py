import csv
import hashlib
import sqlite3
import math
import os

# Haversine distance helper
def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371.0 * 2 * math.asin(math.sqrt(a))

def get_hash(lat: float, lon: float) -> str:
    coord_str = f"{round(lat, 5)},{round(lon, 5)}"
    return hashlib.md5(coord_str.encode()).hexdigest()[:12]

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    csv_path = os.path.join(root_dir, "layer2_3_gateway", "ingestion", "sample_data", "hue_pois.csv")
    locations = []
    
    # Add hotel (Hue Century Riverside Hotel)
    locations.append({
        "name": "Hue Century Riverside Hotel",
        "latitude": 16.4637,
        "longitude": 107.5905
    })
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            locations.append({
                "name": row["name"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"])
            })
            
    print(f"Total locations to seed: {len(locations)}")
    
    db_paths = [
        os.path.join(root_dir, "distance_cache.db"),
        os.path.join(root_dir, "fleet-route-optimizer-cvrptw", "distance_cache.db")
    ]
    
    for db_path in db_paths:
        print(f"Seeding database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations_v2 (
                location_hash TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS distances_v2 (
                from_hash TEXT NOT NULL,
                to_hash TEXT NOT NULL,
                mode TEXT NOT NULL,
                distance_km REAL NOT NULL,
                duration_min REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (from_hash, to_hash, mode),
                FOREIGN KEY (from_hash) REFERENCES locations_v2(location_hash),
                FOREIGN KEY (to_hash) REFERENCES locations_v2(location_hash)
            )
        """)
        
        # Insert locations
        for loc in locations:
            h = get_hash(loc["latitude"], loc["longitude"])
            cursor.execute(
                "INSERT OR REPLACE INTO locations_v2 (location_hash, latitude, longitude) VALUES (?, ?, ?)",
                (h, loc["latitude"], loc["longitude"])
            )
            
        # Insert pairwise taxi distances
        inserted_count = 0
        for loc1 in locations:
            h1 = get_hash(loc1["latitude"], loc1["longitude"])
            for loc2 in locations:
                h2 = get_hash(loc2["latitude"], loc2["longitude"])
                dist = haversine_distance(loc1["latitude"], loc1["longitude"], loc2["latitude"], loc2["longitude"])
                dur = (dist / 30.0) * 60.0 # 30km/h taxi speed
                cursor.execute(
                    "INSERT OR REPLACE INTO distances_v2 (from_hash, to_hash, mode, distance_km, duration_min) VALUES (?, ?, ?, ?, ?)",
                    (h1, h2, "taxi", dist, dur)
                )
                inserted_count += 1
                
        conn.commit()
        conn.close()
        print(f"Done seeding {db_path}! Inserted {inserted_count} distance pairs.")

if __name__ == "__main__":
    main()
