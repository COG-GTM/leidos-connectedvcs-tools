"""CoT XML builder.

Converts CoTEvent dataclass instances into MIL-STD-6017 compliant
XML strings for consumption by TAK Server and TAK clients (ATAK/WinTAK).
"""

from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Optional

from cv2tak.cot.models import CoTEvent


_COT_DATE_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _fmt_time(dt: Optional[datetime]) -> str:
    """Format a datetime to CoT timestamp string."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(_COT_DATE_FMT)


def build_cot_xml(event: CoTEvent) -> str:
    """Serialize a CoTEvent to a CoT XML string.

    Args:
        event: The CoTEvent dataclass to serialize.

    Returns:
        A UTF-8 encoded XML string conforming to MIL-STD-6017.
    """
    root = Element("event")
    root.set("version", "2.0")
    root.set("uid", event.uid)
    root.set("type", event.cot_type)
    root.set("how", event.how)
    root.set("time", _fmt_time(event.time))
    root.set("start", _fmt_time(event.start))
    root.set("stale", _fmt_time(event.stale))

    if event.opex:
        root.set("opex", event.opex)
    if event.access:
        root.set("access", event.access)
    if event.qos:
        root.set("qos", event.qos)

    # <point>
    pt = SubElement(root, "point")
    pt.set("lat", f"{event.point.lat:.7f}")
    pt.set("lon", f"{event.point.lon:.7f}")
    pt.set("hae", f"{event.point.hae:.1f}")
    pt.set("ce", f"{event.point.ce:.1f}")
    pt.set("le", f"{event.point.le:.1f}")

    # <detail>
    detail_el = SubElement(root, "detail")

    # <contact>
    if event.contact:
        contact_el = SubElement(detail_el, "contact")
        contact_el.set("callsign", event.contact.callsign)
        if event.contact.endpoint:
            contact_el.set("endpoint", event.contact.endpoint)
        if event.contact.phone:
            contact_el.set("phone", event.contact.phone)

    # <track>
    if event.track:
        track_el = SubElement(detail_el, "track")
        track_el.set("speed", f"{event.track.speed:.1f}")
        track_el.set("course", f"{event.track.course:.1f}")

    # Custom detail attributes and children
    if event.detail:
        for key, value in event.detail.attrs.items():
            detail_el.set(key, value)

        for child_tag, child_attrs in event.detail.children.items():
            child_el = SubElement(detail_el, child_tag)
            for attr_key, attr_val in child_attrs.items():
                child_el.set(attr_key, attr_val)

        if event.detail.remarks:
            remarks_el = SubElement(detail_el, "remarks")
            remarks_el.text = event.detail.remarks

    xml_bytes = tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>{xml_bytes}'


def build_cot_xml_bytes(event: CoTEvent) -> bytes:
    """Serialize a CoTEvent to CoT XML bytes (UTF-8).

    Suitable for sending over TCP/UDP sockets.

    Args:
        event: The CoTEvent dataclass to serialize.

    Returns:
        UTF-8 encoded bytes of the CoT XML.
    """
    return build_cot_xml(event).encode("utf-8")
