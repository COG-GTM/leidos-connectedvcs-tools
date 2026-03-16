"""Connected Vehicle data simulator.

Generates realistic synthetic J2735 messages for testing the cv2tak
bridge without requiring a live V2X radio or RSU data feed.

Simulates:
- BSMs: Vehicles driving along predefined routes
- TIMs: Road hazards and work zone advisories
- MAP: Intersection geometry
- SPaT: Signal phase cycling
"""

import logging
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator, List, Optional, Tuple

from cv2tak.cv.models import (
    Approach,
    BasicSafetyMessage,
    BSMCoreData,
    ITISCode,
    Lane,
    LaneDirection,
    LaneNode,
    LaneType,
    MapData,
    PhaseState,
    Position3D,
    SignalPhaseState,
    SPaTMessage,
    TIMDuration,
    TIMRegion,
    TransmissionState,
    TravelerInformationMessage,
    VehicleType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geographic constants for simulation scenarios
# ---------------------------------------------------------------------------

# Washington DC area - common test location for USDOT CV pilots
DC_CENTER = Position3D(latitude=38.8977, longitude=-77.0365, elevation=15.0)

# Turner-Fairbank Highway Research Center (FHWA) - McLean, VA
TFHRC_CENTER = Position3D(latitude=38.9548, longitude=-77.1467, elevation=100.0)

# New York City - Times Square area
NYC_CENTER = Position3D(latitude=40.7580, longitude=-73.9855, elevation=10.0)

# Sample intersection: US-50 & Gallows Rd, Fairfax VA (USDOT CV pilot site)
FAIRFAX_INTERSECTION = Position3D(latitude=38.8642, longitude=-77.2270, elevation=85.0)


@dataclass
class SimulatedVehicle:
    """A simulated vehicle moving along a path."""

    temp_id: str
    vehicle_type: VehicleType
    position: Position3D
    speed: float  # m/s
    heading: float  # degrees
    msg_count: int = 0

    def advance(self, dt: float) -> None:
        """Move the vehicle forward by dt seconds along its heading."""
        distance = self.speed * dt  # meters
        dlat = (distance * math.cos(math.radians(self.heading))) / 111320.0
        dlon = (
            distance
            * math.sin(math.radians(self.heading))
            / (111320.0 * math.cos(math.radians(self.position.latitude)))
        )
        self.position = Position3D(
            latitude=self.position.latitude + dlat,
            longitude=self.position.longitude + dlon,
            elevation=self.position.elevation,
        )
        # Add slight heading variation for realism
        self.heading = (self.heading + random.uniform(-2.0, 2.0)) % 360
        # Vary speed slightly
        self.speed = max(0.5, self.speed + random.uniform(-0.5, 0.5))
        self.msg_count = (self.msg_count + 1) % 128


def _random_temp_id() -> str:
    """Generate a random 4-byte temporary ID as hex."""
    return f"{random.randint(0, 0xFFFFFFFF):08X}"


def create_sample_vehicles(
    center: Position3D,
    count: int = 5,
    radius_m: float = 500.0,
) -> List[SimulatedVehicle]:
    """Create a set of simulated vehicles around a center point.

    Args:
        center: The geographic center to scatter vehicles around.
        count: Number of vehicles to create.
        radius_m: Radius in meters to scatter vehicles within.

    Returns:
        List of SimulatedVehicle instances.
    """
    vehicles: List[SimulatedVehicle] = []
    vehicle_types = [VehicleType.PASSENGER, VehicleType.BUS, VehicleType.TRUCK,
                     VehicleType.EMERGENCY, VehicleType.MOTORCYCLE]

    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, radius_m)
        dlat = (dist * math.cos(angle)) / 111320.0
        dlon = dist * math.sin(angle) / (111320.0 * math.cos(math.radians(center.latitude)))

        vehicles.append(
            SimulatedVehicle(
                temp_id=_random_temp_id(),
                vehicle_type=random.choice(vehicle_types),
                position=Position3D(
                    latitude=center.latitude + dlat,
                    longitude=center.longitude + dlon,
                    elevation=center.elevation + random.uniform(-2, 2),
                ),
                speed=random.uniform(5.0, 25.0),  # 5-25 m/s (~11-56 mph)
                heading=random.uniform(0, 360),
            )
        )

    return vehicles


def generate_bsm(vehicle: SimulatedVehicle) -> BasicSafetyMessage:
    """Generate a BSM from a simulated vehicle's current state."""
    core = BSMCoreData(
        msg_count=vehicle.msg_count,
        temporary_id=vehicle.temp_id,
        position=vehicle.position,
        speed=vehicle.speed,
        heading=vehicle.heading,
        transmission=TransmissionState.FORWARD_GEARS,
        vehicle_size_width=1.8 if vehicle.vehicle_type != VehicleType.TRUCK else 2.6,
        vehicle_size_length=4.5 if vehicle.vehicle_type != VehicleType.TRUCK else 12.0,
    )
    return BasicSafetyMessage(
        core_data=core,
        vehicle_type=vehicle.vehicle_type,
    )


def generate_sample_tim() -> TravelerInformationMessage:
    """Generate a sample TIM for a work zone near the FHWA TFHRC."""
    return TravelerInformationMessage(
        msg_id="TIM-WZ-001",
        itis_codes=[ITISCode.WORK_ZONE, ITISCode.REDUCED_SPEED, ITISCode.LANE_CLOSED],
        regions=[
            TIMRegion(
                anchor=Position3D(38.8660, -77.2250, 85.0),
                direction=45.0,
                extent=800.0,
                description="US-50 EB Work Zone: Right lane closed, reduce speed to 35 mph",
            ),
            TIMRegion(
                anchor=Position3D(38.8680, -77.2200, 85.0),
                direction=45.0,
                extent=400.0,
                description="US-50 EB: Merge left, construction ahead",
            ),
        ],
        priority=6,
        duration=TIMDuration.MINUTES_60,
    )


def generate_sample_map() -> MapData:
    """Generate a sample MAP message for a 4-way intersection."""
    intersection = MapData(
        intersection_id=12345,
        name="US-50 & Gallows Rd",
        reference_point=FAIRFAX_INTERSECTION,
        revision=1,
    )

    approach_configs = [
        ("Northbound Gallows Rd", 0, LaneDirection.INBOUND),
        ("Southbound Gallows Rd", 180, LaneDirection.INBOUND),
        ("Eastbound US-50", 90, LaneDirection.INBOUND),
        ("Westbound US-50", 270, LaneDirection.INBOUND),
    ]

    for idx, (name, bearing, direction) in enumerate(approach_configs, start=1):
        approach = Approach(approach_id=idx, name=name)
        for lane_idx in range(3):  # 3 lanes per approach
            offset = (lane_idx - 1) * 3.7  # lane offset in meters
            rad = math.radians(bearing + 90)
            dlat = (offset * math.cos(rad)) / 111320.0
            dlon = offset * math.sin(rad) / (
                111320.0 * math.cos(math.radians(FAIRFAX_INTERSECTION.latitude))
            )

            node_start = LaneNode(
                position=Position3D(
                    FAIRFAX_INTERSECTION.latitude + dlat,
                    FAIRFAX_INTERSECTION.longitude + dlon,
                    FAIRFAX_INTERSECTION.elevation,
                )
            )

            lane = Lane(
                lane_id=idx * 10 + lane_idx,
                lane_type=LaneType.VEHICLE,
                direction=direction,
                nodes=[node_start],
            )
            approach.lanes.append(lane)

        intersection.approaches.append(approach)

    return intersection


def generate_sample_spat(
    intersection_id: int = 12345,
    name: str = "US-50 & Gallows Rd",
) -> SPaTMessage:
    """Generate a sample SPaT message with cycling phases."""
    cycle_sec = time.time() % 90  # 90-second cycle

    phases: List[PhaseState] = []

    # Signal groups 1-4 (N/S/E/W through movements)
    for sg in range(1, 5):
        offset = (sg - 1) * 22.5  # stagger phases
        phase_pos = (cycle_sec + offset) % 90

        if phase_pos < 35:
            state = SignalPhaseState.PROTECTED_GREEN
        elif phase_pos < 40:
            state = SignalPhaseState.PROTECTED_YELLOW
        else:
            state = SignalPhaseState.STOP_AND_REMAIN

        phases.append(PhaseState(signal_group=sg, state=state))

    # Signal groups 5-8 (left turn movements)
    for sg in range(5, 9):
        offset = (sg - 5) * 22.5 + 10
        phase_pos = (cycle_sec + offset) % 90

        if phase_pos < 8:
            state = SignalPhaseState.PROTECTED_GREEN
        elif phase_pos < 11:
            state = SignalPhaseState.PROTECTED_YELLOW
        else:
            state = SignalPhaseState.STOP_AND_REMAIN

        phases.append(PhaseState(signal_group=sg, state=state))

    return SPaTMessage(
        intersection_id=intersection_id,
        name=name,
        phases=phases,
        revision=1,
    )


def bsm_stream(
    vehicles: Optional[List[SimulatedVehicle]] = None,
    center: Optional[Position3D] = None,
    vehicle_count: int = 5,
    interval: float = 0.1,
) -> Generator[BasicSafetyMessage, None, None]:
    """Generate a continuous stream of BSMs from simulated vehicles.

    This is an infinite generator that yields BSMs at the specified
    interval, simulating a live V2X data feed.

    Args:
        vehicles: Pre-created vehicles, or None to auto-generate.
        center: Center point for auto-generated vehicles.
        vehicle_count: Number of vehicles if auto-generating.
        interval: Time between BSMs per vehicle (seconds). Default 0.1s = 10 Hz.

    Yields:
        BasicSafetyMessage instances from each vehicle in round-robin.
    """
    if vehicles is None:
        if center is None:
            center = FAIRFAX_INTERSECTION
        vehicles = create_sample_vehicles(center, vehicle_count)

    logger.info("Starting BSM stream with %d vehicles", len(vehicles))

    while True:
        for vehicle in vehicles:
            vehicle.advance(interval)
            yield generate_bsm(vehicle)
        time.sleep(interval)
