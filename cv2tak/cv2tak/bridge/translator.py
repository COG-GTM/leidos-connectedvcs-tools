"""CV to CoT translator.

Converts Connected Vehicle J2735 messages into CoT events suitable
for display on TAK clients (ATAK, WinTAK, iTAK).
"""

import logging
from datetime import timedelta
from typing import List

from cv2tak.cot.models import (
    CoTContact,
    CoTDetail,
    CoTEvent,
    CoTPoint,
    CoTTrack,
    CoTType,
)
from cv2tak.cv.models import (
    BasicSafetyMessage,
    ITISCode,
    MapData,
    SignalPhaseState,
    SPaTMessage,
    TravelerInformationMessage,
    VehicleType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vehicle type to CoT type mapping
# ---------------------------------------------------------------------------

_VEHICLE_COT_TYPES = {
    VehicleType.PASSENGER: CoTType.NEUTRAL_GROUND_VEHICLE.value,
    VehicleType.BUS: CoTType.NEUTRAL_GROUND_VEHICLE.value,
    VehicleType.TRUCK: CoTType.NEUTRAL_GROUND_VEHICLE.value,
    VehicleType.MOTORCYCLE: CoTType.NEUTRAL_GROUND_VEHICLE.value,
    VehicleType.EMERGENCY: CoTType.FRIEND_GROUND_VEHICLE.value,
    VehicleType.BICYCLE: CoTType.NEUTRAL_GROUND.value,
    VehicleType.PEDESTRIAN: CoTType.NEUTRAL_GROUND.value,
    VehicleType.NONE: CoTType.UNKNOWN_GROUND.value,
}

_VEHICLE_CALLSIGN_PREFIX = {
    VehicleType.PASSENGER: "VEH",
    VehicleType.BUS: "BUS",
    VehicleType.TRUCK: "TRK",
    VehicleType.MOTORCYCLE: "MCY",
    VehicleType.EMERGENCY: "EMG",
    VehicleType.BICYCLE: "BIC",
    VehicleType.PEDESTRIAN: "PED",
    VehicleType.NONE: "UNK",
}


# ---------------------------------------------------------------------------
# ITIS code to CoT type mapping for TIM
# ---------------------------------------------------------------------------

_ITIS_COT_TYPES = {
    ITISCode.WORK_ZONE: CoTType.WORK_ZONE.value,
    ITISCode.ROAD_CONSTRUCTION: CoTType.WORK_ZONE.value,
    ITISCode.ROAD_MAINTENANCE: CoTType.WORK_ZONE.value,
    ITISCode.ACCIDENT: CoTType.ROAD_HAZARD.value,
    ITISCode.INCIDENT: CoTType.ROAD_HAZARD.value,
    ITISCode.FLOODING: CoTType.ROAD_HAZARD.value,
    ITISCode.ICE_ON_ROAD: CoTType.ROAD_HAZARD.value,
    ITISCode.SNOW_ON_ROAD: CoTType.ROAD_HAZARD.value,
    ITISCode.STOPPED_TRAFFIC: CoTType.ROAD_HAZARD.value,
    ITISCode.SLOW_TRAFFIC: CoTType.ROAD_HAZARD.value,
    ITISCode.LONG_QUEUES: CoTType.ROAD_HAZARD.value,
    ITISCode.LANE_CLOSED: CoTType.ROAD_HAZARD.value,
    ITISCode.SHOULDER_CLOSED: CoTType.ROAD_HAZARD.value,
    ITISCode.SPEED_LIMIT: CoTType.POINT.value,
    ITISCode.REDUCED_SPEED: CoTType.POINT.value,
}


# ---------------------------------------------------------------------------
# Signal phase state to color mapping
# ---------------------------------------------------------------------------

_PHASE_COLORS = {
    SignalPhaseState.DARK: "000000",
    SignalPhaseState.STOP_THEN_PROCEED: "FF0000",
    SignalPhaseState.STOP_AND_REMAIN: "FF0000",
    SignalPhaseState.PRE_MOVEMENT: "FFFF00",
    SignalPhaseState.PERMISSIVE_GREEN: "00FF00",
    SignalPhaseState.PROTECTED_GREEN: "00FF00",
    SignalPhaseState.PERMISSIVE_YELLOW: "FFFF00",
    SignalPhaseState.PROTECTED_YELLOW: "FFFF00",
    SignalPhaseState.CAUTION: "FFA500",
}


def bsm_to_cot(bsm: BasicSafetyMessage) -> CoTEvent:
    """Convert a Basic Safety Message to a CoT event.

    Each BSM becomes a single moving marker on the TAK map representing
    a connected vehicle with its current position, speed, and heading.

    Args:
        bsm: The BasicSafetyMessage to convert.

    Returns:
        A CoTEvent representing the vehicle.
    """
    core = bsm.core_data
    cot_type = _VEHICLE_COT_TYPES.get(bsm.vehicle_type, CoTType.UNKNOWN_GROUND.value)
    prefix = _VEHICLE_CALLSIGN_PREFIX.get(bsm.vehicle_type, "UNK")
    callsign = f"{prefix}-{core.temporary_id[:4].upper()}"

    stale_time = bsm.timestamp + timedelta(seconds=10) if bsm.timestamp else None

    detail = CoTDetail(
        children={
            "__cv_bsm": {
                "msgCount": str(core.msg_count),
                "tempId": core.temporary_id,
                "transmission": str(core.transmission.name),
                "vehicleType": bsm.vehicle_type.name,
                "width": f"{core.vehicle_size_width:.1f}",
                "length": f"{core.vehicle_size_length:.1f}",
            },
        },
        remarks=f"CV BSM | {bsm.vehicle_type.name} | Speed: {core.speed:.1f} m/s",
    )

    return CoTEvent(
        uid=f"CV-BSM-{core.temporary_id}",
        cot_type=cot_type,
        point=CoTPoint(
            lat=core.position.latitude,
            lon=core.position.longitude,
            hae=core.position.elevation,
            ce=5.0,  # GPS-level accuracy
            le=10.0,
        ),
        how="m-g",  # machine GPS
        time=bsm.timestamp,
        stale=stale_time,
        contact=CoTContact(callsign=callsign),
        track=CoTTrack(speed=core.speed, course=core.heading),
        detail=detail,
    )


def tim_to_cot(tim: TravelerInformationMessage) -> List[CoTEvent]:
    """Convert a Traveler Information Message to CoT events.

    Each TIM region becomes a separate CoT point marker with the
    advisory information in the detail/remarks fields.

    Args:
        tim: The TravelerInformationMessage to convert.

    Returns:
        A list of CoTEvents, one per TIM region.
    """
    events: List[CoTEvent] = []

    # Determine CoT type from the first ITIS code
    cot_type = CoTType.ROAD_HAZARD.value
    if tim.itis_codes:
        cot_type = _ITIS_COT_TYPES.get(tim.itis_codes[0], CoTType.ROAD_HAZARD.value)

    itis_names = [code.name for code in tim.itis_codes]
    remarks = f"CV TIM | {', '.join(itis_names)} | Priority: {tim.priority}"

    stale_delta = timedelta(minutes=tim.duration.value)

    for idx, region in enumerate(tim.regions):
        detail = CoTDetail(
            children={
                "__cv_tim": {
                    "msgId": tim.msg_id,
                    "priority": str(tim.priority),
                    "duration": str(tim.duration.value),
                    "itisCodes": ",".join(str(c.value) for c in tim.itis_codes),
                    "direction": f"{region.direction:.1f}",
                    "extent": f"{region.extent:.0f}",
                },
            },
            remarks=f"{remarks}\n{region.description}" if region.description else remarks,
        )

        events.append(
            CoTEvent(
                uid=f"CV-TIM-{tim.msg_id}-{idx}",
                cot_type=cot_type,
                point=CoTPoint(
                    lat=region.anchor.latitude,
                    lon=region.anchor.longitude,
                    hae=region.anchor.elevation,
                ),
                how="m-g",
                time=tim.timestamp,
                stale=tim.timestamp + stale_delta if tim.timestamp else None,
                contact=CoTContact(callsign=f"TIM-{tim.msg_id[:6]}"),
                detail=detail,
            )
        )

    return events


def map_to_cot(map_data: MapData) -> CoTEvent:
    """Convert a MAP message to a CoT event.

    The intersection reference point becomes a single CoT marker
    with lane and approach metadata in the detail block.

    Args:
        map_data: The MapData to convert.

    Returns:
        A CoTEvent representing the intersection.
    """
    total_lanes = sum(len(a.lanes) for a in map_data.approaches)
    approach_names = [a.name for a in map_data.approaches if a.name]

    detail = CoTDetail(
        children={
            "__cv_map": {
                "intersectionId": str(map_data.intersection_id),
                "name": map_data.name,
                "revision": str(map_data.revision),
                "approachCount": str(len(map_data.approaches)),
                "laneCount": str(total_lanes),
            },
        },
        remarks=(
            f"CV MAP | {map_data.name} | "
            f"{len(map_data.approaches)} approaches, {total_lanes} lanes"
            + (f"\nApproaches: {', '.join(approach_names)}" if approach_names else "")
        ),
    )

    return CoTEvent(
        uid=f"CV-MAP-{map_data.intersection_id}",
        cot_type=CoTType.TRAFFIC_SIGNAL.value,
        point=CoTPoint(
            lat=map_data.reference_point.latitude,
            lon=map_data.reference_point.longitude,
            hae=map_data.reference_point.elevation,
        ),
        how="m-g",
        time=map_data.timestamp,
        stale=map_data.timestamp + timedelta(hours=24) if map_data.timestamp else None,
        contact=CoTContact(callsign=f"INT-{map_data.intersection_id}"),
        detail=detail,
    )


def spat_to_cot(spat: SPaTMessage) -> CoTEvent:
    """Convert a SPaT message to a CoT event.

    The intersection becomes a CoT marker with current signal phase
    information in the detail block, color-coded by the dominant phase.

    Args:
        spat: The SPaTMessage to convert.

    Returns:
        A CoTEvent representing the intersection signal state.
    """
    # Find the dominant phase state (first green, else first yellow, else red)
    dominant_color = "FF0000"
    for phase in spat.phases:
        color = _PHASE_COLORS.get(phase.state, "FF0000")
        if color == "00FF00":
            dominant_color = color
            break
        if color == "FFFF00" and dominant_color == "FF0000":
            dominant_color = color

    phase_summary = ", ".join(
        f"SG{p.signal_group}:{p.state.value}" for p in spat.phases
    )

    detail = CoTDetail(
        children={
            "__cv_spat": {
                "intersectionId": str(spat.intersection_id),
                "name": spat.name,
                "revision": str(spat.revision),
                "phaseCount": str(len(spat.phases)),
                "dominantColor": dominant_color,
            },
            "color": {
                "argb": f"FF{dominant_color}",
            },
        },
        remarks=f"CV SPaT | {spat.name} | {phase_summary}",
    )

    return CoTEvent(
        uid=f"CV-SPAT-{spat.intersection_id}",
        cot_type=CoTType.TRAFFIC_SIGNAL.value,
        point=CoTPoint(lat=0.0, lon=0.0),  # Must be enriched from MAP data
        how="m-g",
        time=spat.timestamp,
        stale=spat.timestamp + timedelta(seconds=5) if spat.timestamp else None,
        contact=CoTContact(callsign=f"SIG-{spat.intersection_id}"),
        detail=detail,
    )


def enrich_spat_position(
    spat_event: CoTEvent, map_data: MapData
) -> CoTEvent:
    """Enrich a SPaT CoT event with position from the matching MAP message.

    SPaT messages don't contain position data; they reference an intersection
    by ID. This function copies the reference point from the corresponding
    MAP message.

    Args:
        spat_event: The CoT event generated from a SPaT message.
        map_data: The MAP data for the same intersection.

    Returns:
        The same CoTEvent with updated position.
    """
    spat_event.point.lat = map_data.reference_point.latitude
    spat_event.point.lon = map_data.reference_point.longitude
    spat_event.point.hae = map_data.reference_point.elevation
    return spat_event
