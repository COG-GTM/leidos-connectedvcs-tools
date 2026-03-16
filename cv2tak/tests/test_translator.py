"""Tests for CV to CoT translation."""

from cv2tak.bridge.translator import (
    bsm_to_cot,
    enrich_spat_position,
    map_to_cot,
    spat_to_cot,
    tim_to_cot,
)
from cv2tak.cot.models import CoTType
from cv2tak.cv.models import (
    Approach,
    BasicSafetyMessage,
    BSMCoreData,
    ITISCode,
    Lane,
    MapData,
    PhaseState,
    Position3D,
    SignalPhaseState,
    SPaTMessage,
    TIMRegion,
    TravelerInformationMessage,
    VehicleType,
)


class TestBSMToCoT:
    def _make_bsm(self, **kwargs):
        defaults = {
            "msg_count": 1,
            "temporary_id": "AABB1122",
            "position": Position3D(38.8977, -77.0365, 15.0),
            "speed": 15.0,
            "heading": 90.0,
        }
        defaults.update(kwargs)
        core = BSMCoreData(**defaults)
        return BasicSafetyMessage(core_data=core)

    def test_bsm_produces_cot_event(self):
        bsm = self._make_bsm()
        event = bsm_to_cot(bsm)

        assert event.uid == "CV-BSM-AABB1122"
        assert event.point.lat == 38.8977
        assert event.point.lon == -77.0365
        assert event.contact is not None
        assert event.track is not None
        assert event.track.speed == 15.0
        assert event.track.course == 90.0

    def test_bsm_emergency_vehicle_is_friendly(self):
        bsm = self._make_bsm()
        bsm.vehicle_type = VehicleType.EMERGENCY
        event = bsm_to_cot(bsm)

        assert event.cot_type == CoTType.FRIEND_GROUND_VEHICLE.value

    def test_bsm_passenger_is_neutral(self):
        bsm = self._make_bsm()
        bsm.vehicle_type = VehicleType.PASSENGER
        event = bsm_to_cot(bsm)

        assert event.cot_type == CoTType.NEUTRAL_GROUND_VEHICLE.value

    def test_bsm_detail_contains_cv_metadata(self):
        bsm = self._make_bsm()
        event = bsm_to_cot(bsm)

        assert event.detail is not None
        assert "__cv_bsm" in event.detail.children
        assert event.detail.children["__cv_bsm"]["tempId"] == "AABB1122"


class TestTIMToCoT:
    def test_tim_produces_events_per_region(self):
        tim = TravelerInformationMessage(
            msg_id="TIM-001",
            itis_codes=[ITISCode.WORK_ZONE],
            regions=[
                TIMRegion(anchor=Position3D(38.86, -77.22, 85.0)),
                TIMRegion(anchor=Position3D(38.87, -77.21, 85.0)),
            ],
        )
        events = tim_to_cot(tim)

        assert len(events) == 2
        assert events[0].uid == "CV-TIM-TIM-001-0"
        assert events[1].uid == "CV-TIM-TIM-001-1"

    def test_tim_work_zone_type(self):
        tim = TravelerInformationMessage(
            msg_id="TIM-002",
            itis_codes=[ITISCode.WORK_ZONE],
            regions=[TIMRegion(anchor=Position3D(38.86, -77.22, 85.0))],
        )
        events = tim_to_cot(tim)

        assert events[0].cot_type == CoTType.WORK_ZONE.value

    def test_tim_accident_type(self):
        tim = TravelerInformationMessage(
            msg_id="TIM-003",
            itis_codes=[ITISCode.ACCIDENT],
            regions=[TIMRegion(anchor=Position3D(38.86, -77.22, 85.0))],
        )
        events = tim_to_cot(tim)

        assert events[0].cot_type == CoTType.ROAD_HAZARD.value


class TestMAPToCoT:
    def test_map_produces_cot_event(self):
        map_data = MapData(
            intersection_id=12345,
            name="Test Intersection",
            reference_point=Position3D(38.8642, -77.2270, 85.0),
            approaches=[
                Approach(
                    approach_id=1,
                    name="Northbound",
                    lanes=[Lane(lane_id=1), Lane(lane_id=2)],
                ),
            ],
        )
        event = map_to_cot(map_data)

        assert event.uid == "CV-MAP-12345"
        assert event.cot_type == CoTType.TRAFFIC_SIGNAL.value
        assert event.point.lat == 38.8642
        assert event.detail is not None
        assert "__cv_map" in event.detail.children
        assert event.detail.children["__cv_map"]["laneCount"] == "2"


class TestSPaTToCoT:
    def test_spat_produces_cot_event(self):
        spat = SPaTMessage(
            intersection_id=12345,
            name="Test Intersection",
            phases=[
                PhaseState(signal_group=1, state=SignalPhaseState.PROTECTED_GREEN),
            ],
        )
        event = spat_to_cot(spat)

        assert event.uid == "CV-SPAT-12345"
        assert event.cot_type == CoTType.TRAFFIC_SIGNAL.value
        assert event.detail is not None

    def test_spat_green_dominant_color(self):
        spat = SPaTMessage(
            intersection_id=1,
            name="Test",
            phases=[
                PhaseState(signal_group=1, state=SignalPhaseState.PROTECTED_GREEN),
                PhaseState(signal_group=2, state=SignalPhaseState.STOP_AND_REMAIN),
            ],
        )
        event = spat_to_cot(spat)

        assert event.detail.children["__cv_spat"]["dominantColor"] == "00FF00"

    def test_enrich_spat_position(self):
        spat = SPaTMessage(
            intersection_id=12345,
            name="Test",
            phases=[],
        )
        spat_event = spat_to_cot(spat)
        assert spat_event.point.lat == 0.0  # default before enrichment

        map_data = MapData(
            intersection_id=12345,
            name="Test",
            reference_point=Position3D(38.8642, -77.2270, 85.0),
        )
        enriched = enrich_spat_position(spat_event, map_data)

        assert enriched.point.lat == 38.8642
        assert enriched.point.lon == -77.2270
