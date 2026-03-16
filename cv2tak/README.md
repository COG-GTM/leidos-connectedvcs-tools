# cv2tak — Connected Vehicle to TAK Bridge

Translates SAE J2735 Connected Vehicle (V2X) messages into MIL-STD-6017 Cursor on Target (CoT) XML events for real-time display on TAK clients (ATAK, WinTAK, iTAK).

## Architecture

```
┌─────────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  CV Data Source      │      │  cv2tak Bridge   │      │  TAK Ecosystem  │
│                      │      │                  │      │                 │
│  BSM  (vehicles)    ─┼──►  │  J2735 Models    │      │  TAK Server     │
│  TIM  (advisories)  ─┼──►  │       │          │      │       │         │
│  MAP  (geometry)    ─┼──►  │       ▼          │      │       ▼         │
│  SPaT (signals)     ─┼──►  │  Translator      │──►  │  ATAK / WinTAK  │
│                      │      │       │          │      │  iTAK / WebTAK  │
│  (or Simulator)      │      │       ▼          │      │                 │
│                      │      │  CoT XML Builder │      │  CoT Markers:   │
│                      │      │       │          │      │  • Vehicles     │
│                      │      │       ▼          │      │  • Hazards      │
│                      │      │  Transport       │      │  • Signals      │
│                      │      │  (TCP/UDP/File)  │      │  • Intersections│
└─────────────────────┘      └──────────────────┘      └─────────────────┘
```

## Supported Message Types

| J2735 Message | CoT Representation | Description |
|---|---|---|
| **BSM** (Basic Safety Message) | Moving vehicle track | Position, speed, heading for each equipped vehicle |
| **TIM** (Traveler Information Message) | Hazard/advisory marker | Work zones, accidents, road conditions with ITIS codes |
| **MAP** (Map Application) | Intersection marker | Intersection geometry with approaches and lanes |
| **SPaT** (Signal Phase and Timing) | Signal status marker | Traffic signal phases, color-coded by dominant state |

## Quick Start

### Install

```bash
cd cv2tak
pip install -e .
```

### Run with stdout (no TAK Server needed)

```bash
cv2tak --protocol stdout --vehicles 3 --interval 2
```

This starts the simulator with 3 vehicles near Fairfax, VA and prints CoT XML events to the console every 2 seconds.

### Run with TAK Server

```bash
# TCP connection (default TAK streaming port)
cv2tak --host 192.168.1.100 --port 8087 --protocol tcp

# UDP multicast (TAK SA channel)
cv2tak --host 239.2.3.1 --port 6969 --protocol udp

# With TLS
cv2tak --host tak.example.com --port 8089 --protocol tcp --tls
```

### Run with config file

```bash
cv2tak --config config.yaml
```

### Write to file

```bash
cv2tak --protocol file --output events.xml
```

## Configuration

Configuration is loaded from (in order of precedence):
1. CLI arguments
2. Environment variables (`CV2TAK_HOST`, `CV2TAK_PORT`, etc.)
3. YAML config file
4. Built-in defaults

See `config.yaml` for all available options.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `CV2TAK_HOST` | TAK Server host | `127.0.0.1` |
| `CV2TAK_PORT` | TAK Server port | `8087` |
| `CV2TAK_PROTOCOL` | Transport protocol | `tcp` |
| `CV2TAK_TLS` | Enable TLS | `false` |
| `CV2TAK_VEHICLE_COUNT` | Simulated vehicles | `5` |
| `CV2TAK_BSM_INTERVAL` | BSM update interval (sec) | `1.0` |
| `CV2TAK_LOG_LEVEL` | Log level | `INFO` |

## Project Structure

```
cv2tak/
├── cv2tak/
│   ├── __init__.py          # Package init, version
│   ├── main.py              # CLI entry point
│   ├── config.py            # YAML/env configuration
│   ├── cot/
│   │   ├── models.py        # CoT dataclasses (CoTEvent, CoTPoint, etc.)
│   │   ├── builder.py       # CoT XML serialization
│   │   └── transport.py     # TCP/UDP/File/Stdout transports
│   ├── cv/
│   │   ├── models.py        # J2735 message models (BSM, TIM, MAP, SPaT)
│   │   └── simulator.py     # Synthetic CV data generator
│   └── bridge/
│       └── translator.py    # CV → CoT translation logic
├── tests/
│   ├── test_cot_builder.py  # CoT XML generation tests
│   ├── test_cv_models.py    # CV model tests
│   └── test_translator.py   # Translation logic tests
├── examples/
│   ├── sample_bsm.json      # Example BSM payload
│   └── sample_tim.json      # Example TIM payload
├── config.yaml              # Example configuration
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
└── README.md                # This file
```

## CoT Type Mappings

### Vehicle Types (BSM)

| Vehicle Type | CoT Type | Affiliation |
|---|---|---|
| Passenger | `a-n-G-E-V` | Neutral ground vehicle |
| Bus | `a-n-G-E-V` | Neutral ground vehicle |
| Truck | `a-n-G-E-V` | Neutral ground vehicle |
| Emergency | `a-f-G-E-V` | Friendly ground vehicle |
| Motorcycle | `a-n-G-E-V` | Neutral ground vehicle |

### Advisory Types (TIM)

| ITIS Category | CoT Type | Icon |
|---|---|---|
| Work Zone / Construction | `b-r-.-O-M-R-W` | Work zone marker |
| Accident / Incident | `b-r-.-O-M-R-H` | Road hazard |
| Weather (ice, snow, flood) | `b-r-.-O-M-R-H` | Road hazard |
| Traffic (stopped, slow) | `b-r-.-O-M-R-H` | Road hazard |

## Development

### Run tests

```bash
cd cv2tak
pip install -e ".[dev]"
pytest tests/ -v
```

### Example: Generate a single BSM CoT event

```python
from cv2tak.cv.models import BasicSafetyMessage, BSMCoreData, Position3D
from cv2tak.bridge.translator import bsm_to_cot
from cv2tak.cot.builder import build_cot_xml

bsm = BasicSafetyMessage(
    core_data=BSMCoreData(
        msg_count=1,
        temporary_id="AABB1122",
        position=Position3D(38.8977, -77.0365, 15.0),
        speed=15.0,
        heading=90.0,
    )
)

cot_event = bsm_to_cot(bsm)
print(build_cot_xml(cot_event))
```

## Integration with ConnectedVCS Tools

This prototype is designed to complement the existing `leidos-connectedvcs-tools` ecosystem:

- **fedgov-cv-message-builder**: Provides J2735 ASN.1 UPER encoding/decoding. cv2tak can consume decoded messages from this tool.
- **fedgov-cv-TIMcreator-webapp**: Creates TIM messages via web UI. cv2tak can translate these TIMs to CoT for TAK display.
- **fedgov-cv-ISDcreator-webapp**: Creates Intersection Situation Data. The MAP/SPaT models in cv2tak align with the ISD data structures.

## Dependencies

- Python 3.8+
- PyYAML (configuration parsing)
- No additional external dependencies for core functionality
