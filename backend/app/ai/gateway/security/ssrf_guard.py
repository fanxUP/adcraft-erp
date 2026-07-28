"""SSRF protection for custom provider Base URLs.

Prevents the system from making requests to internal/private IPs
when administrators configure custom model provider URLs.
"""
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

_BLOCKED_PREFIXES = [
    "127.",
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
]

_BLOCKED_HOSTS = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]


class SSRFError(Exception):
    """Raised when a URL would resolve to a blocked/internal address."""


def validate_url(url: str, allow_internal: bool = False) -> str:
    """Validate that a URL does not point to an internal/private address.

    Raises SSRFError if the URL resolves to a blocked address.
    Returns the original URL on success.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""

    # Check known blocked hosts
    if host.lower() in _BLOCKED_HOSTS:
        raise SSRFError(f"Blocked host: {host}")

    # Resolve hostname to IP(s)
    try:
        ips = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise SSRFError(f"Cannot resolve hostname: {host}")

    for family, _, _, _, sockaddr in ips:
        ip_str = sockaddr[0]

        # Parse IP
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Check against private ranges
        for private_range in _PRIVATE_RANGES:
            if ip_obj in private_range:
                if not allow_internal:
                    raise SSRFError(f"URL resolves to private IP: {ip_str}")
                break

    return url
