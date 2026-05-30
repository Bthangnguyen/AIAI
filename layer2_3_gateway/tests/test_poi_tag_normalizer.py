from app.services.poi_tag_normalizer import normalize_tags


def test_normalize_broken_json_array_tags_for_cafe():
    tags = ['["địa phương"', '"ẩm thực"', '"thư giãn"', '"cà phê"', '"đồ uống"]']

    normalized = normalize_tags(
        name="Muối Coffee",
        category="cafe",
        category_group="cafe",
        description="Cà phê muối địa phương ở Huế",
        raw_tags=tags,
    )

    assert "cafe" in normalized
    assert "cafe_muoi" in normalized
    assert "local_cafe" not in normalized
    assert "am_thuc" not in normalized


def test_food_micro_tags_are_specific():
    normalized = normalize_tags(
        name="Bún Bò Huế Bà Tuyết",
        category="food",
        category_group="food",
        description="Quán bún bò Huế đường phố",
        raw_tags=["restaurant", "ẩm thực", "món huế"],
    )

    assert "food" in normalized
    assert "bun_bo" in normalized
    assert "street_food" in normalized
    assert "restaurant" not in normalized
