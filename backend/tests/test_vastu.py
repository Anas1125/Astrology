from app.services.vastu import analyze_vastu_rooms, direction_for_point


def test_top_edge_north_maps_image_corners_to_compass_zones():
    assert direction_for_point(0.05, 0.05, "top") == "North-West"
    assert direction_for_point(0.95, 0.05, "top") == "North-East"
    assert direction_for_point(0.95, 0.95, "top") == "South-East"
    assert direction_for_point(0.05, 0.95, "top") == "South-West"


def test_selected_north_edge_rotates_room_direction():
    assert direction_for_point(0.95, 0.5, "right") == "North"
    assert direction_for_point(0.5, 0.95, "bottom") == "North"
    assert direction_for_point(0.05, 0.5, "left") == "North"


def test_kitchen_in_southeast_gets_traditional_preference_not_a_score():
    result = analyze_vastu_rooms([{"room_type": "kitchen", "x": 0.85, "y": 0.85}], "top")
    assert result["rooms"][0]["direction"] == "South-East"
    assert result["rooms"][0]["status"] == "preferred"
    assert "score" not in result


def test_bathroom_guidance_is_not_forced_into_pass_fail():
    result = analyze_vastu_rooms([{"room_type": "bathroom", "x": 0.5, "y": 0.5}], "top")
    assert result["rooms"][0]["status"] == "varies"


def test_rejects_missing_or_out_of_bounds_room_markers():
    try:
        analyze_vastu_rooms([], "top")
    except ValueError as exc:
        assert "between 1 and 20" in str(exc)
    else:
        raise AssertionError("Expected empty markers to be rejected")

    try:
        direction_for_point(1.2, 0.5, "top")
    except ValueError as exc:
        assert "inside" in str(exc)
    else:
        raise AssertionError("Expected invalid marker coordinates to be rejected")
