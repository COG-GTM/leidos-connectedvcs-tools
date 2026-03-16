"""Tests for CoT XML builder."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from cv2tak.cot.builder import build_cot_xml, build_cot_xml_bytes
from cv2tak.cot.models import (
    CoTContact,
    CoTDetail,
    CoTEvent,
    CoTPoint,
    CoTTrack,
)


def _make_event(**kwargs):
    """Create a minimal CoTEvent for testing."""
    defaults = {
        "uid": "TEST-001",
        "cot_type": "a-f-G-E-V",
        "point": CoTPoint(lat=38.8977, lon=-77.0365, hae=15.0),
    }
    defaults.update(kwargs)
    return CoTEvent(**defaults)


class TestBuildCoTXML:
    def test_basic_event_produces_valid_xml(self):
        event = _make_event()
        xml_str = build_cot_xml(event)

        assert xml_str.startswith('<?xml version="1.0"')
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))
        assert root.tag == "event"
        assert root.get("uid") == "TEST-001"
        assert root.get("type") == "a-f-G-E-V"
        assert root.get("version") == "2.0"

    def test_point_element(self):
        event = _make_event(
            point=CoTPoint(lat=40.7580, lon=-73.9855, hae=10.0, ce=5.0, le=8.0)
        )
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        pt = root.find("point")
        assert pt is not None
        assert pt.get("lat") == "40.7580000"
        assert pt.get("lon") == "-73.9855000"
        assert pt.get("hae") == "10.0"
        assert pt.get("ce") == "5.0"
        assert pt.get("le") == "8.0"

    def test_contact_element(self):
        event = _make_event(
            contact=CoTContact(callsign="VEH-1234", endpoint="10.0.0.1:4242:tcp")
        )
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        detail = root.find("detail")
        contact = detail.find("contact")
        assert contact is not None
        assert contact.get("callsign") == "VEH-1234"
        assert contact.get("endpoint") == "10.0.0.1:4242:tcp"

    def test_track_element(self):
        event = _make_event(
            track=CoTTrack(speed=15.5, course=270.0)
        )
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        detail = root.find("detail")
        track = detail.find("track")
        assert track is not None
        assert track.get("speed") == "15.5"
        assert track.get("course") == "270.0"

    def test_detail_with_remarks(self):
        event = _make_event(
            detail=CoTDetail(remarks="Test vehicle on I-66")
        )
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        remarks = root.find(".//remarks")
        assert remarks is not None
        assert remarks.text == "Test vehicle on I-66"

    def test_detail_with_children(self):
        event = _make_event(
            detail=CoTDetail(
                children={
                    "__cv_bsm": {"tempId": "AABB1122", "speed": "15.0"}
                }
            )
        )
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        bsm_el = root.find(".//__cv_bsm")
        assert bsm_el is not None
        assert bsm_el.get("tempId") == "AABB1122"
        assert bsm_el.get("speed") == "15.0"

    def test_bytes_output(self):
        event = _make_event()
        result = build_cot_xml_bytes(event)
        assert isinstance(result, bytes)
        assert result.startswith(b"<?xml")

    def test_time_attributes_present(self):
        now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = _make_event(time=now, start=now)
        xml_str = build_cot_xml(event)
        root = ET.fromstring(xml_str.replace('<?xml version="1.0" encoding="UTF-8"?>', ""))

        assert root.get("time") is not None
        assert root.get("start") is not None
        assert root.get("stale") is not None
        assert "2026-03-15" in root.get("time")
