import pytest
from src.models.domain import Location, TransportMode
from src.services.distance_cache import DistanceCacheService

@pytest.fixture
def distance_service():
    return DistanceCacheService()

def test_unreachable_node_fallback(distance_service):
    """
    Test 1.1: Điểm mù không gian (Unreachable Node)
    Kịch bản: P16 nằm giữa sông Hương hoặc không có đường dẫn.
    Kỳ vọng: OSRM không được sập, DistanceCacheService phải tự động fallback sang Haversine (chim bay) cho điểm bị lỗi,
    và trả về ma trận hợp lệ cho OR-Tools mà không báo lỗi mismatch.
    """
    # Đại Nội Huế (Hợp lệ)
    loc_valid = Location(latitude=16.468450, longitude=107.579002)
    # Tọa độ giữa đại dương/giữa sông (Không thể route bằng đường bộ)
    loc_unreachable = Location(latitude=16.450000, longitude=107.570000)
    
    locations = [loc_valid, loc_unreachable]
    
    matrix = distance_service.build_matrix(locations, TransportMode.TAXI)
    
    # Assert dimensions
    assert len(matrix) == 4 # 2x2 = 4 pairs
    
    loc1 = (loc_valid.latitude, loc_valid.longitude)
    loc2 = (loc_unreachable.latitude, loc_unreachable.longitude)
    
    dist_1_2, time_1_2 = matrix[(loc1, loc2)]
    dist_2_1, time_2_1 = matrix[(loc2, loc1)]
    dist_1_1, time_1_1 = matrix[(loc1, loc1)]
    dist_2_2, time_2_2 = matrix[(loc2, loc2)]
    
    # Assert fallback values (distance from A to B shouldn't be exactly 0, but a positive haversine distance)
    # Since it falls back to Haversine, distance > 0, time > 0
    assert dist_1_2 > 0
    assert dist_2_1 > 0
    assert time_1_2 > 0
    assert time_2_1 > 0
    
    # Check that diagonal is 0
    assert dist_1_1 == 0
    assert dist_2_2 == 0

def test_one_way_trap(distance_service):
    """
    Test 1.2: Bẫy đường một chiều (One-way Trap)
    Kịch bản: Chọn 2 điểm trên đường một chiều.
    Kỳ vọng: Ma trận bất đối xứng (A -> B != B -> A).
    """
    # Chọn 2 điểm gần Đại Nội (đường 1 chiều) hoặc một vòng cung. 
    # Ví dụ: Lê Duẩn hoặc Trần Hưng Đạo.
    # Điểm A: Đầu đường 1 chiều
    loc_a = Location(latitude=16.474661, longitude=107.588820) # Chợ Đông Ba
    # Điểm B: Điểm bên kia đường
    loc_b = Location(latitude=16.471649, longitude=107.590057) # Cầu Tràng Tiền
    
    locations = [loc_a, loc_b]
    matrix = distance_service.build_matrix(locations, TransportMode.TAXI)
    
    tup_a = (loc_a.latitude, loc_a.longitude)
    tup_b = (loc_b.latitude, loc_b.longitude)
    
    dist_a_to_b, _ = matrix[(tup_a, tup_b)]
    dist_b_to_a, _ = matrix[(tup_b, tup_a)]
    
    # In reality, going A->B might be shorter than going B->A due to U-turns / one way.
    # As long as they are slightly different, the matrix is asymmetric.
    # Note: If they are perfectly symmetric, it means OSRM profile doesn't enforce one-ways or the road is two-way.
    # Hue OSRM profile handles this.
    assert dist_a_to_b != dist_b_to_a, f"Expected asymmetric distances, but got {dist_a_to_b} for both directions"
