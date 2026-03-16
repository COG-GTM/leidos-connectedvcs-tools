"""SAE J2735 Connected Vehicle message data models.

Simplified Python representations of the key J2735 message types
used in V2X (Vehicle-to-Everything) communication. These models
capture the fields relevant for TAK visualization.

Reference: SAE J2735 (2024 revision)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------

@dataclass
class Position3D:
    """WGS-84 position (J2735 Position3D)."""

    latitude: float   # decimal degrees (-90 to 90)
    longitude: float  # decimal degrees (-180 to 180)
    elevation: float = 0.0  # meters above WGS-84 ellipsoid


@dataclass
class AccelerationSet4Way:
    """Vehicle acceleration (J2735 AccelerationSet4Way)."""

    longitudinal: float = 0.0  # m/s^2
    lateral: float = 0.0       # m/s^2
    vertical: float = 0.0      # m/s^2
    yaw_rate: float = 0.0      # deg/s


# ---------------------------------------------------------------------------
# BSM - Basic Safety Message (J2735 MessageFrame id=20)
# ---------------------------------------------------------------------------

class TransmissionState(IntEnum):
    """Vehicle transmission state (J2735 TransmissionState)."""

    NEUTRAL = 0
    PARK = 1
    FORWARD_GEARS = 2
    REVERSE_GEARS = 3
    UNAVAILABLE = 7


class VehicleType(IntEnum):
    """Vehicle classification."""

    NONE = 0
    PASSENGER = 1
    BUS = 2
    EMERGENCY = 3
    TRUCK = 4
    MOTORCYCLE = 5
    BICYCLE = 6
    PEDESTRIAN = 7


@dataclass
class BSMCoreData:
    """BSM Part I - Core Data (always present)."""

    msg_count: int  # 0-127, increments per message
    temporary_id: str  # 4-byte hex string (randomized)
    position: Position3D
    speed: float  # m/s
    heading: float  # degrees (0-359.9875)
    transmission: TransmissionState = TransmissionState.UNAVAILABLE
    accel_set: Optional[AccelerationSet4Way] = None
    brakes: Optional[Dict[str, bool]] = None
    vehicle_size_width: float = 1.8  # meters
    vehicle_size_length: float = 4.5  # meters
    sec_mark: int = 0  # milliseconds into the minute (0-59999)


@dataclass
class BasicSafetyMessage:
    """J2735 Basic Safety Message (BSM).

    The BSM is the primary V2V (Vehicle-to-Vehicle) safety message,
    broadcast at 10 Hz by each equipped vehicle.
    """

    core_data: BSMCoreData
    vehicle_type: VehicleType = VehicleType.PASSENGER
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# TIM - Traveler Information Message (J2735 MessageFrame id=31)
# ---------------------------------------------------------------------------

class ITISCode(IntEnum):
    """Selected ITIS (International Traveler Information Systems) codes."""

    STOPPED_TRAFFIC = 257
    SLOW_TRAFFIC = 258
    LONG_QUEUES = 259
    ROAD_CONSTRUCTION = 769
    ROAD_MAINTENANCE = 770
    WORK_ZONE = 771
    ACCIDENT = 513
    INCIDENT = 514
    FLOODING = 3073
    ICE_ON_ROAD = 3585
    SNOW_ON_ROAD = 3586
    SPEED_LIMIT = 8720
    REDUCED_SPEED = 7937
    LANE_CLOSED = 1025
    SHOULDER_CLOSED = 1026


class TIMDuration(IntEnum):
    """TIM duration values (minutes)."""

    MINUTES_1 = 1
    MINUTES_5 = 5
    MINUTES_10 = 10
    MINUTES_15 = 15
    MINUTES_30 = 30
    MINUTES_60 = 60
    MINUTES_120 = 120
    MINUTES_720 = 720
    MINUTES_1440 = 1440


@dataclass
class TIMRegion:
    """Geographic region for a TIM advisory."""

    anchor: Position3D
    lane_width: float = 3.7  # meters
    direction: float = 0.0   # heading in degrees
    extent: float = 1000.0   # length along road in meters
    description: str = ""


@dataclass
class TravelerInformationMessage:
    """J2735 Traveler Information Message (TIM).

    TIMs provide advisory information about road conditions, work zones,
    incidents, and other hazards to equipped vehicles and infrastructure.
    """

    msg_id: str
    itis_codes: List[ITISCode]
    regions: List[TIMRegion]
    priority: int = 5  # 0 (lowest) to 7 (highest)
    duration: TIMDuration = TIMDuration.MINUTES_30
    start_time: Optional[datetime] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc)
        if self.timestamp is None:
            self.timestamp = now
        if self.start_time is None:
            self.start_time = now


# ---------------------------------------------------------------------------
# MAP - Map Data (J2735 MessageFrame id=18)
# ---------------------------------------------------------------------------

class LaneDirection(Enum):
    """Direction of travel for a lane."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BOTH = "both"


class LaneType(Enum):
    """Type of lane."""

    VEHICLE = "vehicle"
    CROSSWALK = "crosswalk"
    BIKE = "bike"
    SIDEWALK = "sidewalk"
    MEDIAN = "median"
    STRIPING = "striping"
    TRACKED_VEHICLE = "trackedVehicle"
    PARKING = "parking"


@dataclass
class LaneNode:
    """A single node in a lane geometry."""

    position: Position3D
    lane_width: Optional[float] = None  # meters (overrides default)


@dataclass
class Lane:
    """A single lane within an approach."""

    lane_id: int
    lane_type: LaneType = LaneType.VEHICLE
    direction: LaneDirection = LaneDirection.INBOUND
    nodes: List[LaneNode] = field(default_factory=list)
    lane_width: float = 3.7  # meters (default)
    shared_with: Optional[List[str]] = None  # signal groups
    maneuvers: Optional[List[str]] = None  # allowed maneuvers


@dataclass
class Approach:
    """An intersection approach containing lanes."""

    approach_id: int
    name: str = ""
    lanes: List[Lane] = field(default_factory=list)


@dataclass
class MapData:
    """J2735 MAP (Map Application) message.

    Describes the geometry of an intersection including approaches,
    lanes, crosswalks, and signal group associations.
    """

    intersection_id: int
    name: str
    reference_point: Position3D
    approaches: List[Approach] = field(default_factory=list)
    revision: int = 0
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# SPaT - Signal Phase and Timing (J2735 MessageFrame id=19)
# ---------------------------------------------------------------------------

class SignalPhaseState(Enum):
    """Traffic signal phase state."""

    DARK = "dark"
    STOP_THEN_PROCEED = "stop-Then-Proceed"
    STOP_AND_REMAIN = "stop-And-Remain"
    PRE_MOVEMENT = "pre-Movement"
    PERMISSIVE_GREEN = "permissive-Movement-Allowed"
    PROTECTED_GREEN = "protected-Movement-Allowed"
    PERMISSIVE_YELLOW = "permissive-clearance"
    PROTECTED_YELLOW = "protected-clearance"
    CAUTION = "caution-Conflicting-Traffic"


@dataclass
class PhaseState:
    """State of a single signal phase/movement."""

    signal_group: int
    state: SignalPhaseState
    min_end_time: Optional[int] = None  # tenths of seconds from epoch
    max_end_time: Optional[int] = None
    likely_time: Optional[int] = None
    confidence: Optional[int] = None  # 0-15


@dataclass
class SPaTMessage:
    """J2735 Signal Phase and Timing (SPaT) message.

    Provides the current state of traffic signals at an intersection,
    including countdown timing for phase changes.
    """

    intersection_id: int
    name: str
    phases: List[PhaseState] = field(default_factory=list)
    revision: int = 0
    status: int = 0  # IntersectionStatusObject bitmask
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
