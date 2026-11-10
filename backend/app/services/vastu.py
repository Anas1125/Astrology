"""Deterministic, image-assisted Vastu room-zone observations.

Room positions are user-marked on a floor-plan preview. This module does not
perform automatic room recognition, infer north, or make structural claims.
"""
from __future__ import annotations

import math
from typing import Any

NORTH_SIDES = {"top", "right", "bottom", "left"}
ROOM_TYPES = {
    "kitchen", "master_bedroom", "bedroom", "prayer_room", "bathroom",
    "living_room", "study_room", "dining_room", "other",
}

_DIRECTION_TA = {
    "North": "வடக்கு", "North-East": "வடகிழக்கு", "East": "கிழக்கு",
    "South-East": "தென்கிழக்கு", "South": "தெற்கு",
    "South-West": "தென்மேற்கு", "West": "மேற்கு",
    "North-West": "வடமேற்கு", "Centre": "மையம்",
}
_ROOM_TA = {
    "kitchen": "சமையலறை", "master_bedroom": "முதன்மை படுக்கையறை",
    "bedroom": "படுக்கையறை", "prayer_room": "பூஜை அறை",
    "bathroom": "குளியலறை", "living_room": "வரவேற்பறை",
    "study_room": "படிப்பு அறை", "dining_room": "உணவருந்தும் அறை",
    "other": "மற்ற அறை",
}
_ROOM_EN = {
    "kitchen": "Kitchen", "master_bedroom": "Master bedroom",
    "bedroom": "Bedroom", "prayer_room": "Prayer room",
    "bathroom": "Bathroom / toilet", "living_room": "Living room",
    "study_room": "Study room", "dining_room": "Dining room", "other": "Other room",
}
_PREFERRED = {
    "kitchen": "South-East",
    "master_bedroom": "South-West",
    "bedroom": "South",
    "prayer_room": "North-East",
}
_ALTERNATIVES = {
    "kitchen": {"North-West"},
    "master_bedroom": {"South", "West"},
    "bedroom": {"South-West", "West", "North-West"},
    "prayer_room": {"East", "North"},
}
_GRID = (
    ("North-West", "North", "North-East"),
    ("West", "Centre", "East"),
    ("South-West", "South", "South-East"),
)


def direction_for_point(x: float, y: float, north_side: str) -> str:
    """Map normalized building coordinates (not full-image coordinates) to a compass zone."""
    if north_side not in NORTH_SIDES:
        raise ValueError("Choose which edge of the floor plan points north.")
    if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= 1 and 0 <= y <= 1):
        raise ValueError("Room markers must be inside the selected building boundary.")
    if north_side == "top":
        east_x, south_y = x, y
    elif north_side == "right":
        east_x, south_y = y, 1 - x
    elif north_side == "bottom":
        east_x, south_y = 1 - x, 1 - y
    else:
        east_x, south_y = 1 - y, x
    col = min(2, int(east_x * 3))
    row = min(2, int(south_y * 3))
    return _GRID[row][col]


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Solve a small dense system with pivoted Gauss-Jordan elimination."""
    size = len(values)
    augmented = [list(row) + [float(value)] for row, value in zip(matrix, values)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            raise ValueError("The selected building boundary is too narrow or distorted. Mark its four corners again.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [item / divisor for item in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [augmented[index][-1] for index in range(size)]


def _boundary_transform(boundary: list[dict[str, Any]]) -> list[float]:
    """Map a clockwise image quadrilateral to the unit rectangle."""
    if not isinstance(boundary, list) or len(boundary) != 4:
        raise ValueError("Mark all four outer corners of the building boundary.")
    points: list[tuple[float, float]] = []
    for index, point in enumerate(boundary, start=1):
        if not isinstance(point, dict):
            raise ValueError(f"Building boundary corner {index} is invalid.")
        try:
            x, y = float(point.get("x")), float(point.get("y"))
        except (TypeError, ValueError):
            raise ValueError(f"Building boundary corner {index} has invalid coordinates.") from None
        if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("Building boundary corners must be inside the uploaded image.")
        points.append((x, y))
    # In screen coordinates, top-left -> top-right -> bottom-right -> bottom-left is clockwise.
    crosses = []
    for index in range(4):
        a, b, c = points[index], points[(index + 1) % 4], points[(index + 2) % 4]
        crosses.append((b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0]))
    area_twice = sum(points[i][0]*points[(i+1)%4][1] - points[(i+1)%4][0]*points[i][1] for i in range(4))
    if area_twice < 0.01 or any(value <= 1e-6 for value in crosses):
        raise ValueError("Mark the four building corners clockwise, starting at the top-left. The outline must be a convex shape.")
    targets = [(0.0,0.0),(1.0,0.0),(1.0,1.0),(0.0,1.0)]
    matrix: list[list[float]]=[]
    values: list[float]=[]
    for (x,y),(u,v) in zip(points, targets):
        matrix.append([x, y, 1.0, 0.0, 0.0, 0.0, -u*x, -u*y])
        values.append(u)

        matrix.append([0.0, 0.0, 0.0, x, y, 1.0, -v*x, -v*y])
        values.append(v)
    return _solve_linear_system(matrix, values)


def _map_point_to_building(x: float, y: float, transform: list[float]) -> tuple[float, float]:
    h11,h12,h13,h21,h22,h23,h31,h32=transform
    denominator=h31*x+h32*y+1.0
    if abs(denominator)<1e-10:
        raise ValueError("A room marker could not be mapped inside the selected building boundary.")
    u=(h11*x+h12*y+h13)/denominator
    v=(h21*x+h22*y+h23)/denominator
    epsilon=1e-5
    if not (-epsilon<=u<=1+epsilon and -epsilon<=v<=1+epsilon):
        raise ValueError("A room marker is outside the selected building boundary. Move it inside the house outline.")
    return max(0.0,min(1.0,u)), max(0.0,min(1.0,v))


def _room_observation(room_type: str, direction: str, room_number: int) -> dict[str, Any]:
    room_en = _ROOM_EN[room_type]
    room_ta = _ROOM_TA[room_type]
    direction_ta = _DIRECTION_TA[direction]

    if room_type == "bathroom":
        status = "varies"
        title_en = "Bathroom guidance varies by Vastu tradition"
        title_ta = "குளியலறை தொடர்பான வாஸ்து வழிகாட்டுதல் மரபுக்கு மாறுபடும்"
        detail_en = (
            "Traditional references do not use one consistent bathroom zone. "
            "AstroAI does not label this placement as compliant or defective."
        )
        detail_ta = (
            "குளியலறையின் திசை குறித்து பாரம்பரிய குறிப்புகளில் ஒரே மாதிரியான "
            "வழிகாட்டுதல் இல்லை. இதைச் சரி அல்லது தவறு என்று AstroAI வகைப்படுத்தாது."
        )
    elif room_type in _PREFERRED:
        preferred = _PREFERRED[room_type]
        preferred_ta = _DIRECTION_TA[preferred]
        if direction == preferred:
            status = "preferred"
            title_en = f"{room_en} is in a commonly cited preferred zone"
            title_ta = f"{room_ta} பொதுவாகக் குறிப்பிடப்படும் விருப்பத் திசையில் உள்ளது"
            detail_en = f"Some Vastu traditions commonly associate the {preferred} zone with a {room_en.lower()}. This is a traditional association, not a measured outcome."
            detail_ta = f"சில வாஸ்து மரபுகள் {preferred_ta} திசையை {room_ta} அமைப்பதற்கான விருப்பத் திசையாகக் குறிப்பிடுகின்றன. இது பாரம்பரியக் கருத்து மட்டுமே; அளவிடப்பட்ட விளைவு அல்ல."
        elif direction in _ALTERNATIVES.get(room_type, set()):
            status = "alternative"
            title_en = f"{direction} is mentioned as an alternative in some traditions"
            title_ta = f"சில மரபுகளில் {direction_ta} மாற்றுத் திசையாகக் குறிப்பிடப்படுகிறது"
            detail_en = f"The most commonly cited preference for a {room_en.lower()} is {preferred}, but some traditions mention {direction} as an alternative. Practices vary."
            detail_ta = f"{room_ta} அமைப்பதற்குப் பொதுவாக {preferred_ta} குறிப்பிடப்பட்டாலும், சில மரபுகள் {direction_ta} திசையையும் மாற்றாகக் கூறுகின்றன. வழக்கங்கள் மாறுபடும்."
        else:
            status = "review"
            title_en = f"{room_en} is outside this common preferred zone"
            title_ta = f"{room_ta} பொதுவாகக் குறிப்பிடப்படும் விருப்பத் திசைக்கு வெளியே உள்ளது"
            detail_en = f"A commonly cited Vastu preference for this room is {preferred}. This is not a defect finding or a prediction; schools and house constraints vary."
            detail_ta = f"இந்த அறைக்கு பொதுவாகக் குறிப்பிடப்படும் வாஸ்து விருப்பத் திசை {preferred_ta}. இதை குறைபாடு அல்லது கணிப்பு என்று பொருள் கொள்ள வேண்டாம்; மரபுகளும் வீட்டின் நடைமுறைத் தேவைகளும் மாறுபடும்."
    else:
        status = "not_assessed"
        title_en = f"No single placement rule applied to {room_en.lower()}"
        title_ta = f"{room_ta}க்கு ஒரே திசை விதி இவ்வருவாயில் பயன்படுத்தப்படவில்லை"
        detail_en = "This first version only compares a small set of room types with clearer, commonly repeated directional associations."
        detail_ta = "இந்த முதல் பதிப்பு, தெளிவாகவும் பொதுவாகவும் மீண்டும் குறிப்பிடப்படும் சில அறைத் திசை தொடர்புகளை மட்டுமே ஒப்பிடுகிறது."

    return {
        "room_number": room_number,
        "room_type": room_type,
        "room_en": room_en,
        "room_ta": room_ta,
        "direction": direction,
        "direction_ta": direction_ta,
        "status": status,
        "title_en": title_en,
        "title_ta": title_ta,
        "detail_en": detail_en,
        "detail_ta": detail_ta,
    }


def analyze_vastu_rooms(
    rooms: list[dict[str, Any]],
    north_side: str,
    boundary: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if north_side not in NORTH_SIDES:
        raise ValueError("Choose which edge of the floor plan points north.")
    if not isinstance(rooms, list) or not 1 <= len(rooms) <= 20:
        raise ValueError("Mark between 1 and 20 rooms on the floor plan.")
    # Full-image bounds preserve service-call compatibility. The HTTP route requires
    # the user to select four corners explicitly before reaching this function.
    selected_boundary = boundary if boundary is not None else [
        {"x":0.0,"y":0.0},{"x":1.0,"y":0.0},
        {"x":1.0,"y":1.0},{"x":0.0,"y":1.0},
    ]
    transform = _boundary_transform(selected_boundary)
    results: list[dict[str, Any]] = []
    for index, room in enumerate(rooms, start=1):
        if not isinstance(room, dict):
            raise ValueError(f"Room marker {index} is invalid.")
        room_type = room.get("room_type")
        if room_type not in ROOM_TYPES:
            raise ValueError(f"Room marker {index} has an unsupported room type.")
        try:
            image_x, image_y = float(room.get("x")), float(room.get("y"))
        except (TypeError, ValueError):
            raise ValueError(f"Room marker {index} has invalid coordinates.") from None
        if not (math.isfinite(image_x) and math.isfinite(image_y) and 0 <= image_x <= 1 and 0 <= image_y <= 1):
            raise ValueError(f"Room marker {index} must be inside the uploaded image.")
        building_x, building_y = _map_point_to_building(image_x, image_y, transform)
        direction = direction_for_point(building_x, building_y, north_side)
        results.append(_room_observation(room_type, direction, index))
    return {
        "room_count": len(results), "rooms": results, "north_side": north_side,
        "method_en": (
            "Room positions were mapped relative to the four building-boundary corners you selected, "
            "then compared with the north edge you confirmed. The image is not automatically interpreted or stored."
        ),
        "method_ta": (
            "நீங்கள் குறித்த கட்டிடத்தின் நான்கு வெளிப்புற மூலைகளையும் உறுதிப்படுத்திய வடக்குத் திசையையும் கொண்டு "
            "அறைகளின் திசைகள் கணக்கிடப்பட்டன. படம் தானாகப் புரிந்துகொள்ளப்படவோ சேமிக்கப்படவோ இல்லை."
        ),
        "caution_en": (
            "Vastu is a traditional belief system, not a scientific assessment. This report is not an architectural, "
            "structural, fire-safety, ventilation, plumbing, or building-code review. Different Vastu schools vary. "
            "Directional accuracy depends on the boundary corners and north direction selected by the user."
        ),
        "caution_ta": (
            "வாஸ்து ஒரு பாரம்பரிய நம்பிக்கை முறை; அறிவியல் மதிப்பீடு அல்ல. இது கட்டிட வடிவமைப்பு, கட்டமைப்பு, "
            "தீ பாதுகாப்பு, காற்றோட்டம், குழாய் அமைப்பு அல்லது கட்டிட விதிமுறை ஆய்வு அல்ல. வாஸ்து மரபுகள் மாறுபடும். "
            "திசைத் துல்லியம் பயனர் தேர்ந்தெடுத்த கட்டிட மூலைகள் மற்றும் வடக்குத் திசையைப் பொறுத்தது."
        ),
    }
