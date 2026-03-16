"""Tests for Connected Vehicle data models."""

from cv2tak.cv.models import (
    BasicSafetyMessage,
    BSMCoreData,
    ITISCode,
    MapData,
    PhaseState,
    Position3D,
    SignalPhaseState,
    SPaTMessage,
    TIMRegion,
    TransmissionState,
    TravelerInformationMessage,
    VehicleType,
)


class TestBSM:
    def test_create_bsm(self):
        core = BSMCoreData(
            msg_count=42,
            temporary_id="AABB1122",
            position=Position3D(38.8977, -77.0365, 15.0),
            speed=15.0,
            heading=90.0,
        )
        bsm = BasicSafetyMessage(core_data=core)

        assert bsm.core_data.msg_count == 42
        assert bsm.core_data.temporary_id == "AABB1122"
        assert bsm.core_data.speed == 15.0
        assert bsm.vehicle_type == VehicleType.PASSENGER
        assert bsm.timestamp is not None

    def test_bsm_defaults(self):
        core = BSMCoreData(
            msg_count=0,
            temporary_id="00000000",
            position=Position3D(0.0, 0.0),
            speed=0.0,
            heading=0.0,
        )
        bsm = BasicSafetyMessage(core_data=core)

        assert bsm.core_data.transmission == TransmissionState.UNAVAILABLE
        assert bsm.core_data.vehicle_size_width == 1.8
        assert bsm.core_data.vehicle_size_length == 4.5


class TestTIM:
    def test_create_tim(self):
        tim = TravelerInformationMessage(
            msg_id="TIM-001",
            itis_codes=[ITISCode.WORK_ZONE, ITISCode.LANE_CLOSED],
            regions=[
                TIMRegion(
                    anchor=Position3D(38.8660, -77.2250, 85.0),
                    direction=45.0,
                    extent=800.0,
                ),
            ],
            priority=6,
        )

        assert tim.msg_id == "TIM-001"
        assert len(tim.itis_codes) == 2
        assert ITISCode.WORK_ZONE in tim.itis_codes
        assert len(tim.regions) == 1
        assert tim.priority == 6
        assert tim.timestamp is not None


class TestMAP:
    def test_create_map(self):
        map_data = MapData(
            intersection_id=12345,
            name="Test Intersection",
            reference_point=Position3D(38.8642, -77.2270, 85.0),
        )

        assert map_data.intersection_id == 12345
        assert map_data.name == "Test Intersection"
        assert len(map_data.approaches) == 0
        assert map_data.revision == 0
        assert map_data.timestamp is not None


class TestSPaT:
    def test_create_spat(self):
        spat = SPaTMessage(
            intersection_id=12345,
            name="Test Intersection",
            phases=[
                PhaseState(signal_group=1, state=SignalPhaseState.PROTECTED_GREEN),
                PhaseState(signal_group=2, state=SignalPhaseState.STOP_AND_REMAIN),
            ],
        )

        assert spat.intersection_id == 12345
        assert len(spat.phases) == 2
        assert spat.phases[0].state == SignalPhaseState.PROTECTED_GREEN
        assert spat.phases[1].state == SignalPhaseState.STOP_AND_REMAIN
        assert spat.timestamp is not None
