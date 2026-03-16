"""CoT (Cursor on Target) data models.

Implements the MIL-STD-6017 Cursor on Target message specification
used by TAK (Team Awareness Kit) for situational awareness.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional


class CoTType(Enum):
    """Common CoT type codes (2525C symbology mapped to CoT type strings).

    Format: a-{affiliation}-{battle_dimension}-{function}
    Affiliations: f=friendly, h=hostile, n=neutral, u=unknown
    Battle dimensions: G=ground, A=air, S=sea, P=space
    """

    # Atoms (points on the map)
    FRIEND_GROUND = "a-f-G"
    FRIEND_GROUND_VEHICLE = "a-f-G-E-V"
    FRIEND_GROUND_EQUIPMENT = "a-f-G-E"
    NEUTRAL_GROUND = "a-n-G"
    NEUTRAL_GROUND_VEHICLE = "a-n-G-E-V"
    UNKNOWN_GROUND = "a-u-G"
    HOSTILE_GROUND = "a-h-G"

    # Bits (shapes/areas)
    ROUTE = "b-m-r"
    POINT = "b-m-p-s-p-i"
    AREA = "b-m-p-s-p-a"
    LINE = "b-m-p-c-l"

    # Infrastructure / transportation
    TRAFFIC_SIGNAL = "a-n-G-I-T-S"
    ROAD_HAZARD = "a-n-G-I-R"
    WORK_ZONE = "a-n-G-I-C"


@dataclass
class CoTPoint:
    """Geographic point for a CoT event."""

    lat: float
    lon: float
    hae: float = 0.0  # Height above ellipsoid (meters)
    ce: float = 999999.0  # Circular error (meters)
    le: float = 999999.0  # Linear error (meters)


@dataclass
class CoTDetail:
    """Detail element for a CoT event.

    Holds key-value metadata and optional sub-elements expressed
    as nested dicts.
    """

    attrs: Dict[str, str] = field(default_factory=dict)
    children: Dict[str, Dict[str, str]] = field(default_factory=dict)
    remarks: Optional[str] = None


@dataclass
class CoTContact:
    """Contact information for a CoT event."""

    callsign: str
    endpoint: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class CoTTrack:
    """Track (motion) data for a CoT event."""

    speed: float = 0.0  # m/s
    course: float = 0.0  # degrees from true north


@dataclass
class CoTEvent:
    """A complete Cursor on Target event.

    This is the fundamental unit of data exchange in the TAK ecosystem.
    Each event represents a single entity or observation with a geographic
    position, type classification, and optional detail metadata.
    """

    uid: str
    cot_type: str  # CoT type string (e.g. "a-f-G-E-V")
    point: CoTPoint
    how: str = "m-g"  # How the position was derived (m-g = machine GPS)
    time: Optional[datetime] = None
    start: Optional[datetime] = None
    stale: Optional[datetime] = None
    contact: Optional[CoTContact] = None
    track: Optional[CoTTrack] = None
    detail: Optional[CoTDetail] = None
    opex: Optional[str] = None  # Operation exercise flag
    access: Optional[str] = None
    qos: Optional[str] = None

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc)
        if self.time is None:
            self.time = now
        if self.start is None:
            self.start = self.time
        if self.stale is None:
            self.stale = self.time + timedelta(seconds=120)

    @staticmethod
    def generate_uid(prefix: str = "CV") -> str:
        """Generate a unique CoT UID with the given prefix."""
        return f"{prefix}-{uuid.uuid4()}"
