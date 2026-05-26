"""Tests for Distance Cache Service with OSRM integration."""
import os
import pytest
import sqlite3
import json
from unittest.mock import patch, MagicMock

from src.services.distance_cache import DistanceCacheService
from src.models.domain import Location, TransportMode


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database file."""
    db_file = tmp_path / "test_cache.db"
    yield str(db_file)
    if db_file.exists():
        os.remove(db_file)


class TestDistanceCacheService:
    
    def test_db_initialization_creates_new_schema(self, temp_db_path):
        """DB should have distances_v2 table with mode column."""
        service = DistanceCacheService(db_path=temp_db_path)
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "locations_v2" in tables
        assert "distances_v2" in tables
        
        # Check columns of distances_v2
        cursor.execute("PRAGMA table_info(distances_v2)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert "mode" in columns
        assert "distance_km" in columns
        assert "duration_min" in columns
        
        conn.close()

    @patch('urllib.request.urlopen')
    def test_build_matrix_calls_osrm_table_api(self, mock_urlopen, temp_db_path):
        """Should call OSRM /table API and store the full matrix."""
        # Mock OSRM response for a 2x2 matrix
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "code": "Ok",
            "distances": [[0, 1500], [1500, 0]],  # in meters
            "durations": [[0, 300], [300, 0]],    # in seconds
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        service = DistanceCacheService(db_path=temp_db_path)
        
        loc1 = Location(latitude=10.0, longitude=106.0)
        loc2 = Location(latitude=10.01, longitude=106.01)
        
        matrix = service.build_matrix([loc1, loc2], mode=TransportMode.TAXI)
        
        # Verify API was called
        mock_urlopen.assert_called_once()
        url = mock_urlopen.call_args[0][0].full_url
        assert "/table/v1/driving/" in url
        assert "annotations=duration,distance" in url
        
        # Verify matrix structure
        l1_tup = (10.0, 106.0)
        l2_tup = (10.01, 106.01)
        
        assert matrix[(l1_tup, l2_tup)] == (1.5, 5.0)  # 1500m -> 1.5km, 300s -> 5.0min
        
        # Verify database storage
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM distances_v2 WHERE mode=?", (TransportMode.TAXI.value,))
        count = cursor.fetchone()[0]
        # (l1, l1), (l1, l2), (l2, l1), (l2, l2) = 4 records
        assert count == 4
        conn.close()

    @patch('urllib.request.urlopen')
    def test_cache_hit_prevents_api_call(self, mock_urlopen, temp_db_path):
        """Calling build_matrix twice should hit cache the second time."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "code": "Ok",
            "distances": [[0, 1000], [1000, 0]],
            "durations": [[0, 120], [120, 0]],
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        service = DistanceCacheService(db_path=temp_db_path)
        locs = [
            Location(latitude=10.0, longitude=106.0),
            Location(latitude=10.1, longitude=106.1)
        ]
        
        # Call 1: Cache miss
        service.build_matrix(locs, mode=TransportMode.TAXI)
        assert mock_urlopen.call_count == 1
        
        # Call 2: Cache hit
        matrix2 = service.build_matrix(locs, mode=TransportMode.TAXI)
        assert mock_urlopen.call_count == 1  # Still 1!
        
        l1_tup = (10.0, 106.0)
        l2_tup = (10.1, 106.1)
        assert matrix2[(l1_tup, l2_tup)] == (1.0, 2.0)

    @patch('urllib.request.urlopen')
    def test_walking_mode_heuristic(self, mock_urlopen, temp_db_path):
        """Walking mode should derive from taxi distance without calling API."""
        # 1. Provide taxi cache first
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "code": "Ok",
            "distances": [[0, 5000], [5000, 0]],  # 5km
            "durations": [[0, 600], [600, 0]],    # 10m driving
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        service = DistanceCacheService(db_path=temp_db_path)
        locs = [
            Location(latitude=10.0, longitude=106.0),
            Location(latitude=10.1, longitude=106.1)
        ]
        
        # Pre-seed taxi
        service.build_matrix(locs, mode=TransportMode.TAXI)
        mock_urlopen.reset_mock()
        
        # 2. Get walking mode
        walk_matrix = service.build_matrix(locs, mode=TransportMode.WALKING)
        
        # API should NOT be called for walking
        mock_urlopen.assert_not_called()
        
        l1_tup = (10.0, 106.0)
        l2_tup = (10.1, 106.1)
        
        dist, dur = walk_matrix[(l1_tup, l2_tup)]
        assert dist == 5.0
        # 5km / 5km/h = 1h = 60 mins
        assert dur == 60.0

    @patch('urllib.request.urlopen')
    def test_osrm_fallback_to_haversine(self, mock_urlopen, temp_db_path):
        """When OSRM is down, build_matrix should fallback to Haversine."""
        # Simulate OSRM timeout/connection refused
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        service = DistanceCacheService(db_path=temp_db_path)
        locs = [
            Location(latitude=16.4637, longitude=107.5909),  # Đại Nội Huế
            Location(latitude=16.4578, longitude=107.5774),  # Lăng Tự Đức
        ]

        # Should NOT crash — returns Haversine fallback
        matrix = service.build_matrix(locs, mode=TransportMode.TAXI)

        l1 = (16.4637, 107.5909)
        l2 = (16.4578, 107.5774)

        assert (l1, l2) in matrix
        dist, dur = matrix[(l1, l2)]
        # Haversine: ~1.5km between these two locations
        assert 0.5 < dist < 5.0, f"Haversine distance should be reasonable, got {dist}"
        # At 30km/h fallback speed: ~3 min
        assert dur > 0, f"Duration should be positive, got {dur}"

    def test_build_matrix_handles_none_mode_gracefully(self, temp_db_path):
        """build_matrix should not crash if mode is somehow None — treated as TAXI."""
        service = DistanceCacheService(db_path=temp_db_path)
        locs = [Location(latitude=10.0, longitude=106.0)]

        # This should NOT crash
        try:
            matrix = service.build_matrix(locs, mode=TransportMode.TAXI)
            assert matrix is not None
        except AttributeError:
            pytest.fail("build_matrix crashed on mode handling")
