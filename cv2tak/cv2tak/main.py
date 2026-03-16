"""cv2tak CLI entry point.

Runs the Connected Vehicle to TAK bridge, translating simulated or
live J2735 messages into CoT events and sending them to a TAK Server.
"""

import argparse
import logging
import signal
import sys
import time
from typing import Optional

from cv2tak import __version__
from cv2tak.bridge.translator import (
    bsm_to_cot,
    enrich_spat_position,
    map_to_cot,
    spat_to_cot,
    tim_to_cot,
)
from cv2tak.config import CV2TAKConfig, load_config
from cv2tak.cot.transport import (
    CoTTransport,
    FileTransport,
    StdoutTransport,
    TCPTransport,
    UDPTransport,
)
from cv2tak.cv.models import Position3D
from cv2tak.cv.simulator import (
    bsm_stream,
    create_sample_vehicles,
    generate_sample_map,
    generate_sample_spat,
    generate_sample_tim,
)

logger = logging.getLogger("cv2tak")

_running = True


def _signal_handler(signum: int, frame: object) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _running
    logger.info("Shutdown signal received, stopping...")
    _running = False


def _create_transport(config: CV2TAKConfig) -> CoTTransport:
    """Create the appropriate transport based on config."""
    protocol = config.tak_server.protocol.lower()

    if protocol == "tcp":
        return TCPTransport(
            host=config.tak_server.host,
            port=config.tak_server.port,
            use_tls=config.tak_server.use_tls,
            certfile=config.tak_server.certfile,
            keyfile=config.tak_server.keyfile,
            cafile=config.tak_server.cafile,
        )
    elif protocol == "udp":
        return UDPTransport(
            host=config.tak_server.host,
            port=config.tak_server.port,
            multicast_iface=config.tak_server.multicast_iface,
            ttl=config.tak_server.ttl,
        )
    elif protocol == "file":
        return FileTransport(filepath=config.tak_server.output_file)
    elif protocol == "stdout":
        return StdoutTransport()
    else:
        raise ValueError(f"Unknown protocol: {protocol}")


def run_bridge(config: CV2TAKConfig) -> None:
    """Run the CV-to-TAK bridge with the given configuration.

    This is the main event loop that:
    1. Creates simulated CV data (or reads from a live source)
    2. Translates CV messages to CoT events
    3. Sends CoT events to the configured TAK transport
    """
    global _running

    transport = _create_transport(config)
    sim = config.simulator

    center = Position3D(
        latitude=sim.center_lat,
        longitude=sim.center_lon,
        elevation=sim.center_elev,
    )
    vehicles = create_sample_vehicles(center, sim.vehicle_count)

    # Pre-generate static messages
    map_data = generate_sample_map() if sim.include_map else None
    tim_data = generate_sample_tim() if sim.include_tim else None

    logger.info("Starting cv2tak bridge v%s", __version__)
    logger.info(
        "Transport: %s | Vehicles: %d | BSM interval: %.1fs",
        config.tak_server.protocol,
        sim.vehicle_count,
        sim.bsm_interval,
    )

    total_sent = 0

    try:
        transport.connect()

        # Send static data first (MAP, TIM)
        if map_data:
            map_event = map_to_cot(map_data)
            transport.send(map_event)
            total_sent += 1
            logger.info("Sent MAP for intersection: %s", map_data.name)

        if tim_data:
            tim_events = tim_to_cot(tim_data)
            for te in tim_events:
                transport.send(te)
                total_sent += 1
            logger.info("Sent %d TIM events", len(tim_events))

        # Main loop: stream BSMs and periodic SPaT updates
        last_spat_time = 0.0
        iteration = 0

        while _running:
            # Generate and send BSMs for all vehicles
            for vehicle in vehicles:
                vehicle.advance(sim.bsm_interval)
                from cv2tak.cv.simulator import generate_bsm

                bsm = generate_bsm(vehicle)
                cot_event = bsm_to_cot(bsm)
                transport.send(cot_event)
                total_sent += 1

            # Periodic SPaT updates
            now = time.time()
            if sim.include_spat and (now - last_spat_time) >= sim.spat_interval:
                spat = generate_sample_spat()
                spat_event = spat_to_cot(spat)
                if map_data:
                    spat_event = enrich_spat_position(spat_event, map_data)
                transport.send(spat_event)
                total_sent += 1
                last_spat_time = now

            iteration += 1
            if iteration % 10 == 0:
                logger.info("Sent %d CoT events total", total_sent)

            time.sleep(sim.bsm_interval)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except ConnectionRefusedError:
        logger.error(
            "Could not connect to TAK Server at %s:%d. "
            "Is the server running? Try --protocol stdout for testing.",
            config.tak_server.host,
            config.tak_server.port,
        )
    finally:
        transport.close()
        logger.info("Bridge stopped. Total CoT events sent: %d", total_sent)


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="cv2tak",
        description="Connected Vehicle to TAK Bridge - Translates J2735 CV messages to CoT events",
    )
    parser.add_argument(
        "--version", action="version", version=f"cv2tak {__version__}"
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="TAK Server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="TAK Server port (default: 8087 for TCP, 6969 for UDP)",
    )
    parser.add_argument(
        "--protocol",
        choices=["tcp", "udp", "file", "stdout"],
        default=None,
        help="Transport protocol (default: tcp)",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=None,
        help="Enable TLS for TCP connections",
    )
    parser.add_argument(
        "--vehicles",
        type=int,
        default=None,
        help="Number of simulated vehicles (default: 5)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Seconds between BSM updates (default: 1.0)",
    )
    parser.add_argument(
        "--center",
        nargs=2,
        type=float,
        metavar=("LAT", "LON"),
        default=None,
        help="Center lat/lon for simulation (default: Fairfax VA)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (for --protocol file)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> None:
    """Main entry point for the cv2tak CLI."""
    args = parse_args(argv)

    # Load config
    config = load_config(args.config)

    # Apply CLI overrides
    if args.host is not None:
        config.tak_server.host = args.host
    if args.port is not None:
        config.tak_server.port = args.port
    if args.protocol is not None:
        config.tak_server.protocol = args.protocol
    if args.tls:
        config.tak_server.use_tls = True
    if args.vehicles is not None:
        config.simulator.vehicle_count = args.vehicles
    if args.interval is not None:
        config.simulator.bsm_interval = args.interval
    if args.center is not None:
        config.simulator.center_lat = args.center[0]
        config.simulator.center_lon = args.center[1]
    if args.output is not None:
        config.tak_server.output_file = args.output
    if args.verbose:
        config.logging.level = "DEBUG"

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format=config.logging.format,
    )

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Run the bridge
    run_bridge(config)


if __name__ == "__main__":
    main()
