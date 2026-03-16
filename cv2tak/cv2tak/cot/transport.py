"""CoT transport layer for TAK Server connectivity.

Supports sending CoT events to TAK Server via:
- TCP: Persistent connection to TAK Server streaming port (default 8087)
- UDP: Connectionless broadcast/multicast (default SA multicast 239.2.3.1:6969)
- File: Write CoT events to a file for offline analysis
"""

import logging
import socket
import ssl
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from cv2tak.cot.builder import build_cot_xml, build_cot_xml_bytes
from cv2tak.cot.models import CoTEvent

logger = logging.getLogger(__name__)


class CoTTransport(ABC):
    """Abstract base class for CoT transport mechanisms."""

    @abstractmethod
    def connect(self) -> None:
        """Establish the transport connection."""

    @abstractmethod
    def send(self, event: CoTEvent) -> None:
        """Send a CoT event."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""

    def __enter__(self) -> "CoTTransport":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


class TCPTransport(CoTTransport):
    """Send CoT events over TCP to a TAK Server streaming interface.

    TAK Server typically listens on port 8087 for streaming TCP connections.
    Each CoT XML message is sent as a complete document.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8087,
        use_tls: bool = False,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cafile: Optional[str] = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile
        self.reconnect_delay = reconnect_delay
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Connect to the TAK Server TCP streaming port."""
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10.0)

        if self.use_tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.certfile and self.keyfile:
                ctx.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            if self.cafile:
                ctx.load_verify_locations(cafile=self.cafile)
            else:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self._sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
        else:
            self._sock = raw_sock

        logger.info("Connecting to TAK Server at %s:%d (TLS=%s)", self.host, self.port, self.use_tls)
        self._sock.connect((self.host, self.port))
        logger.info("Connected to TAK Server at %s:%d", self.host, self.port)

    def send(self, event: CoTEvent) -> None:
        """Send a CoT event over the TCP connection."""
        if self._sock is None:
            raise ConnectionError("Not connected to TAK Server. Call connect() first.")

        payload = build_cot_xml_bytes(event)
        try:
            self._sock.sendall(payload)
            logger.debug("Sent CoT event %s (%d bytes)", event.uid, len(payload))
        except (BrokenPipeError, ConnectionResetError, OSError) as exc:
            logger.warning("Connection lost: %s. Attempting reconnect...", exc)
            self._reconnect()
            self._sock.sendall(payload)

    def _reconnect(self) -> None:
        """Attempt to reconnect after a connection failure."""
        self.close()
        time.sleep(self.reconnect_delay)
        self.connect()

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            logger.info("Disconnected from TAK Server")


class UDPTransport(CoTTransport):
    """Send CoT events over UDP.

    Supports both unicast and multicast. The default TAK SA multicast
    group is 239.2.3.1:6969.
    """

    DEFAULT_MULTICAST_GROUP = "239.2.3.1"
    DEFAULT_MULTICAST_PORT = 6969

    def __init__(
        self,
        host: str = "239.2.3.1",
        port: int = 6969,
        multicast_iface: Optional[str] = None,
        ttl: int = 32,
    ) -> None:
        self.host = host
        self.port = port
        self.multicast_iface = multicast_iface
        self.ttl = ttl
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Create the UDP socket (no connection needed for UDP)."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Check if this is a multicast address (224.0.0.0 - 239.255.255.255)
        first_octet = int(self.host.split(".")[0])
        if 224 <= first_octet <= 239:
            self._sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL,
                self.ttl,
            )
            if self.multicast_iface:
                self._sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(self.multicast_iface),
                )
            logger.info("UDP multicast configured for %s:%d (TTL=%d)", self.host, self.port, self.ttl)
        else:
            logger.info("UDP unicast configured for %s:%d", self.host, self.port)

    def send(self, event: CoTEvent) -> None:
        """Send a CoT event as a UDP datagram."""
        if self._sock is None:
            raise ConnectionError("Socket not initialized. Call connect() first.")

        payload = build_cot_xml_bytes(event)
        self._sock.sendto(payload, (self.host, self.port))
        logger.debug("Sent CoT event %s via UDP (%d bytes)", event.uid, len(payload))

    def close(self) -> None:
        """Close the UDP socket."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


class FileTransport(CoTTransport):
    """Write CoT events to a file for offline analysis or replay.

    Each event is written as a complete XML document separated by newlines.
    Useful for testing without a live TAK Server.
    """

    def __init__(self, filepath: str = "cot_output.xml") -> None:
        self.filepath = Path(filepath)
        self._file = None

    def connect(self) -> None:
        """Open the output file."""
        self._file = open(self.filepath, "a", encoding="utf-8")
        logger.info("Writing CoT events to %s", self.filepath)

    def send(self, event: CoTEvent) -> None:
        """Write a CoT event to the file."""
        if self._file is None:
            raise ConnectionError("File not open. Call connect() first.")

        xml_str = build_cot_xml(event)
        self._file.write(xml_str + "\n")
        self._file.flush()
        logger.debug("Wrote CoT event %s to file", event.uid)

    def close(self) -> None:
        """Close the output file."""
        if self._file is not None:
            self._file.close()
            self._file = None


class StdoutTransport(CoTTransport):
    """Print CoT events to stdout for debugging."""

    def connect(self) -> None:
        """No-op for stdout."""
        logger.info("CoT events will be printed to stdout")

    def send(self, event: CoTEvent) -> None:
        """Print the CoT XML to stdout."""
        xml_str = build_cot_xml(event)
        print(xml_str)

    def close(self) -> None:
        """No-op for stdout."""
