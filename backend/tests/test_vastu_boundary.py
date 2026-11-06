from app.services.vastu import analyze_vastu_rooms, _boundary_transform, _map_point_to_building


def test_boundary_excludes_margins_and_maps_house_relative_kitchen_to_southeast():
    boundary = [{"x":.20,"y":.10},{"x":.80,"y":.10},{"x":.80,"y":.90},{"x":.20,"y":.90}]
    result = analyze_vastu_rooms([{"room_type":"kitchen","x":.68,"y":.74}], "top", boundary)
    assert result["rooms"][0]["direction"] == "South-East"
    assert result["rooms"][0]["status"] == "preferred"


def test_projective_boundary_maps_corners_to_unit_rectangle():
    boundary = [{"x":.25,"y":.15},{"x":.78,"y":.10},{"x":.84,"y":.88},{"x":.18,"y":.82}]
    transform = _boundary_transform(boundary)
    expected = [(0.0,0.0),(1.0,0.0),(1.0,1.0),(0.0,1.0)]
    for point, target in zip(boundary, expected):
        mapped = _map_point_to_building(point["x"], point["y"], transform)
        assert abs(mapped[0]-target[0]) < 1e-8 and abs(mapped[1]-target[1]) < 1e-8


def test_boundary_rejects_wrong_order_and_room_markers_outside_house():
    wrong = [{"x":.2,"y":.1},{"x":.2,"y":.9},{"x":.8,"y":.9},{"x":.8,"y":.1}]
    try:
        analyze_vastu_rooms([{"room_type":"kitchen","x":.5,"y":.5}], "top", wrong)
    except ValueError as exc:
        assert "clockwise" in str(exc)
    else:
        raise AssertionError("Expected wrong boundary order to be rejected")
    boundary = [{"x":.2,"y":.1},{"x":.8,"y":.1},{"x":.8,"y":.9},{"x":.2,"y":.9}]
    try:
        analyze_vastu_rooms([{"room_type":"kitchen","x":.05,"y":.5}], "top", boundary)
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("Expected outside room marker to be rejected")


def test_explicit_empty_boundary_is_rejected_instead_of_using_full_image():
    try:
        analyze_vastu_rooms([{"room_type":"kitchen","x":0.5,"y":0.5}], "top", [])
    except ValueError as exc:
        assert "four outer corners" in str(exc)
    else:
        raise AssertionError("Expected an explicit empty boundary to be rejected")
