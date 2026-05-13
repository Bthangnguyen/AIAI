"""
Distance and travel time cache service using SQLite and OSRM routing service.
Uses the OSRM /table API for efficient bulk matrix fetching.
Supports TransportMode (TAXI, WALKING, etc.).
"""
import sqlite3
import hashlib
import urllib.request
import urllib.error
import json
import time
from typing import List, Tuple, Dict, Set

from ..config import get_logger, get_settings
from ..models.domain import Location, TransportMode
from ..utils import haversine_distance

logger = get_logger(__name__)


class DistanceCacheService:
    """Manages a SQLite cache of distances and travel times between locations."""
    
    def __init__(self, db_path: str = None, osrm_base_url: str = None):
        """
        Initialize the distance cache service.
        """
        settings = get_settings()
        self.db_path = db_path or settings.distance_cache_db
        self.osrm_base_url = osrm_base_url or settings.osrm_base_url
        self._init_db()
    
    def _get_hash(self, lat: float, lon: float) -> str:
        """Create a stable hash for a coordinate pair (rounded to 5 decimals ~1.1m precision)."""
        coord_str = f"{round(lat, 5)},{round(lon, 5)}"
        return hashlib.md5(coord_str.encode()).hexdigest()[:12]
        
    def _init_db(self):
        """Initialize the SQLite database with required tables (v2)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table: locations_v2
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations_v2 (
                location_hash TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table: distances_v2
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
        
        conn.commit()
        conn.close()

    def build_matrix(self, locations: List[Location], mode: TransportMode) -> Dict[Tuple[Tuple[float, float], Tuple[float, float]], Tuple[float, float]]:
        """
        Build a full N*N matrix for the given locations.
        Returns mapping: ((lat1, lon1), (lat2, lon2)) -> (distance_km, duration_min)
        """
        if not locations:
            return {}
            
        # Deduplicate locations
        unique_locs = []
        seen = set()
        for loc in locations:
            tup = (loc.latitude, loc.longitude)
            if tup not in seen:
                seen.add(tup)
                unique_locs.append(loc)
                
        matrix = {}
        missing_pairs = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Fetch from cache
        hashes = [self._get_hash(l.latitude, l.longitude) for l in unique_locs]
        
        # Save unique locs to DB
        for h, loc in zip(hashes, unique_locs):
            cursor.execute(
                "INSERT OR IGNORE INTO locations_v2 (location_hash, latitude, longitude) VALUES (?, ?, ?)",
                (h, loc.latitude, loc.longitude)
            )
        conn.commit()
        
        # If WALKING, try to fetch TAXI distances to use as fallback base
        fetch_mode = TransportMode.TAXI if mode == TransportMode.WALKING else mode
        
        for i, loc1 in enumerate(unique_locs):
            for j, loc2 in enumerate(unique_locs):
                h1 = hashes[i]
                h2 = hashes[j]
                
                cursor.execute(
                    "SELECT distance_km, duration_min FROM distances_v2 WHERE from_hash=? AND to_hash=? AND mode=?",
                    (h1, h2, fetch_mode.value)
                )
                row = cursor.fetchone()
                
                if row:
                    dist_km, dur_min = row
                    if mode == TransportMode.WALKING:
                        # Heuristic: 5 km/h = 83.33 m/min
                        dur_min = dist_km / 5.0 * 60.0
                    
                    matrix[((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))] = (dist_km, dur_min)
                else:
                    missing_pairs.append((i, j))
                    
        conn.close()
        
        # 2. Fetch missing from OSRM if any (fetch full matrix via /table to ensure we have all)
        if missing_pairs and fetch_mode != TransportMode.WALKING: # Only fetch if we need taxi/bus
            logger.info(f"Cache miss for {len(missing_pairs)} pairs. Fetching OSRM table...")
            self._fetch_osrm_table(unique_locs, hashes, fetch_mode)
            
            # Re-read the missing pairs from DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for i, j in missing_pairs:
                loc1 = unique_locs[i]
                loc2 = unique_locs[j]
                h1 = hashes[i]
                h2 = hashes[j]
                
                cursor.execute(
                    "SELECT distance_km, duration_min FROM distances_v2 WHERE from_hash=? AND to_hash=? AND mode=?",
                    (h1, h2, fetch_mode.value)
                )
                row = cursor.fetchone()
                if row:
                    dist_km, dur_min = row
                    matrix[((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))] = (dist_km, dur_min)
                else:
                    # OSRM failed or didn't return this pair -> Haversine fallback
                    dist_km = haversine_distance((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))
                    speed_kmh = 30.0 if mode != TransportMode.WALKING else 5.0
                    dur_min = (dist_km / speed_kmh) * 60.0
                    matrix[((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))] = (dist_km, dur_min)
            conn.close()
            
        elif missing_pairs and fetch_mode == TransportMode.WALKING:
            # If WALKING and no TAXI base found, just use Haversine
            for i, j in missing_pairs:
                loc1 = unique_locs[i]
                loc2 = unique_locs[j]
                dist_km = haversine_distance((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))
                dur_min = (dist_km / 5.0) * 60.0
                matrix[((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude))] = (dist_km, dur_min)

        return matrix

    def _fetch_osrm_table(self, locs: List[Location], hashes: List[str], mode: TransportMode):
        """Fetch full distance/duration table from OSRM and save to DB."""
        if not locs:
            return
            
        coords = ";".join([f"{l.longitude},{l.latitude}" for l in locs])
        url = f"{self.osrm_base_url}/table/v1/driving/{coords}?annotations=duration,distance"
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get('code') == 'Ok':
                    distances = data.get('distances', [])
                    durations = data.get('durations', [])
                    
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    for i in range(len(locs)):
                        for j in range(len(locs)):
                            try:
                                dist_m = distances[i][j]
                                dur_s = durations[i][j]
                                
                                # Handle unroutable pairs
                                if dist_m is None or dur_s is None:
                                    continue
                                    
                                dist_km = dist_m / 1000.0
                                dur_min = dur_s / 60.0
                                
                                cursor.execute(
                                    """
                                    INSERT OR REPLACE INTO distances_v2 
                                    (from_hash, to_hash, mode, distance_km, duration_min) 
                                    VALUES (?, ?, ?, ?, ?)
                                    """,
                                    (hashes[i], hashes[j], mode.value, dist_km, dur_min)
                                )
                            except IndexError:
                                continue
                                
                    conn.commit()
                    conn.close()
                    logger.info(f"Successfully cached OSRM table for {len(locs)} locations.")
                else:
                    logger.warning(f"OSRM returned non-Ok code: {data.get('code')}")
        except Exception as e:
            logger.error(f"Failed to fetch OSRM table: {e}")
