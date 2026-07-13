#!/usr/bin/env python3
"""
Network Scanner
A lightweight, single-file tool for host discovery and TCP port scanning
on networks you own or have permission to test.

Usage:
    python network_scanner.py 192.168.1.0/24              # discover live hosts
    python network_scanner.py 192.168.1.10                # scan common ports on one host
    python network_scanner.py 192.168.1.10 --ports 1-1000  # custom port range
    python network_scanner.py 192.168.1.0/24 --scan-ports  # discover + port-scan each host

Only scan networks and hosts you own or are authorized to test.
"""

import argparse
import ipaddress
import socket
import subprocess
import sys
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCbind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
}


def ping_host(ip: str, timeout: float = 1.0) -> bool:
    """Cross-platform single ping to check if a host is up."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), ip]
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def discover_hosts(network: str, workers: int = 64) -> list:
    net = ipaddress.ip_network(network, strict=False)
    hosts = [str(ip) for ip in net.hosts()]
    live = []

    print(f"Scanning {len(hosts)} addresses in {network} for live hosts...")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(ping_host, ip): ip for ip in hosts}
        for future in as_completed(futures):
            ip = futures[future]
            if future.result():
                live.append(ip)
                print(f"  [+] {ip} is up")

    return sorted(live, key=lambda ip: ipaddress.ip_address(ip))


def scan_port(ip: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((ip, port)) == 0
    except OSError:
        return False


def grab_banner(ip: str, port: int, timeout: float = 1.0) -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port))
            sock.settimeout(timeout)
            try:
                data = sock.recv(128)
                return data.decode(errors="ignore").strip().replace("\r", " ").replace("\n", " ")
            except socket.timeout:
                return ""
    except OSError:
        return ""


def parse_ports(port_spec: str) -> list:
    ports = set()
    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            ports.update(range(int(start), int(end) + 1))
        elif part:
            ports.add(int(part))
    return sorted(ports)


def scan_host_ports(ip: str, ports: list, workers: int = 200, banners: bool = False) -> list:
    open_ports = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scan_port, ip, p): p for p in ports}
        for future in as_completed(futures):
            port = futures[future]
            if future.result():
                open_ports.append(port)

    open_ports.sort()
    print(f"\nOpen ports on {ip}:")
    if not open_ports:
        print("  None found.")
    for port in open_ports:
        service = COMMON_PORTS.get(port, "unknown")
        banner = f"  {grab_banner(ip, port)}" if banners else ""
        print(f"  {port:>5}/tcp  {service:<12}{banner}")

    return open_ports


def main():
    parser = argparse.ArgumentParser(
        description="Discover live hosts and scan TCP ports. Only use on networks you're authorized to test."
    )
    parser.add_argument("target", help="Single IP (10.0.0.5) or CIDR network (10.0.0.0/24)")
    parser.add_argument("--ports", default=None, help="Ports to scan, e.g. '1-1000' or '22,80,443' (default: common ports)")
    parser.add_argument("--scan-ports", action="store_true", help="Also port-scan each live host found in a network sweep")
    parser.add_argument("--banners", action="store_true", help="Attempt to grab service banners on open ports")
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent threads (default: 100)")
    args = parser.parse_args()

    is_network = "/" in args.target
    ports = parse_ports(args.ports) if args.ports else sorted(COMMON_PORTS.keys())

    if is_network:
        live_hosts = discover_hosts(args.target, workers=args.workers)
        print(f"\n{len(live_hosts)} host(s) up.")
        if args.scan_ports:
            for ip in live_hosts:
                scan_host_ports(ip, ports, workers=args.workers, banners=args.banners)
    else:
        ip = args.target
        try:
            socket.inet_aton(ip)
        except OSError:
            print(f"Error: '{ip}' is not a valid IPv4 address.")
            sys.exit(1)
        print(f"Scanning {len(ports)} port(s) on {ip}...")
        scan_host_ports(ip, ports, workers=args.workers, banners=args.banners)


if __name__ == "__main__":
    main()
