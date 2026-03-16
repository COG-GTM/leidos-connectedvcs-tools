"""Configuration management for cv2tak.

Loads configuration from YAML files and environment variables.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class TAKServerConfig:
    """TAK Server connection configuration."""

    host: str = "127.0.0.1"
    port: int = 8087
    protocol: str = "tcp"  # tcp, udp, file, stdout
    use_tls: bool = False
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    cafile: Optional[str] = None
    # UDP multicast settings
    multicast_iface: Optional[str] = None
    ttl: int = 32
    # File output
    output_file: str = "cot_output.xml"


@dataclass
class SimulatorConfig:
    """Simulator configuration."""

    enabled: bool = True
    vehicle_count: int = 5
    center_lat: float = 38.8642
    center_lon: float = -77.2270
    center_elev: float = 85.0
    bsm_interval: float = 1.0  # seconds between BSM batches
    include_tim: bool = True
    include_map: bool = True
    include_spat: bool = True
    spat_interval: float = 1.0  # seconds between SPaT updates


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file: Optional[str] = None


@dataclass
class CV2TAKConfig:
    """Top-level cv2tak configuration."""

    tak_server: TAKServerConfig = field(default_factory=TAKServerConfig)
    simulator: SimulatorConfig = field(default_factory=SimulatorConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(config_path: Optional[str] = None) -> CV2TAKConfig:
    """Load configuration from a YAML file with environment variable overrides.

    Args:
        config_path: Path to YAML config file. If None, uses default config.

    Returns:
        CV2TAKConfig instance.
    """
    config = CV2TAKConfig()

    # Load from YAML file if provided
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if raw:
            _apply_dict(config, raw)
        logger.info("Loaded config from %s", config_path)

    # Override with environment variables
    _apply_env_overrides(config)

    return config


def _apply_dict(config: CV2TAKConfig, raw: dict) -> None:
    """Apply a raw dict (from YAML) to a CV2TAKConfig."""
    if "tak_server" in raw:
        ts = raw["tak_server"]
        for key, val in ts.items():
            if hasattr(config.tak_server, key):
                setattr(config.tak_server, key, val)

    if "simulator" in raw:
        sim = raw["simulator"]
        for key, val in sim.items():
            if hasattr(config.simulator, key):
                setattr(config.simulator, key, val)

    if "logging" in raw:
        log = raw["logging"]
        for key, val in log.items():
            if hasattr(config.logging, key):
                setattr(config.logging, key, val)


def _apply_env_overrides(config: CV2TAKConfig) -> None:
    """Apply environment variable overrides to the config."""
    env_map = {
        "CV2TAK_HOST": ("tak_server", "host"),
        "CV2TAK_PORT": ("tak_server", "port"),
        "CV2TAK_PROTOCOL": ("tak_server", "protocol"),
        "CV2TAK_TLS": ("tak_server", "use_tls"),
        "CV2TAK_CERTFILE": ("tak_server", "certfile"),
        "CV2TAK_KEYFILE": ("tak_server", "keyfile"),
        "CV2TAK_CAFILE": ("tak_server", "cafile"),
        "CV2TAK_VEHICLE_COUNT": ("simulator", "vehicle_count"),
        "CV2TAK_BSM_INTERVAL": ("simulator", "bsm_interval"),
        "CV2TAK_LOG_LEVEL": ("logging", "level"),
    }

    for env_var, (section, attr) in env_map.items():
        val = os.environ.get(env_var)
        if val is not None:
            sub_config = getattr(config, section)
            current = getattr(sub_config, attr)
            if isinstance(current, bool):
                setattr(sub_config, attr, val.lower() in ("true", "1", "yes"))
            elif isinstance(current, int):
                setattr(sub_config, attr, int(val))
            elif isinstance(current, float):
                setattr(sub_config, attr, float(val))
            else:
                setattr(sub_config, attr, val)
            logger.debug("Override from env: %s=%s", env_var, val)
