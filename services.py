#!/usr/bin/env python3
"""
Chronicle Service Management
Start, stop, and manage configured services
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table

console = Console()

# Types
ServiceConfig = Dict[str, Any]
ServicesDict = Dict[str, ServiceConfig]

SERVICES: ServicesDict = {
    "backend": {
        "path": "backends/advanced",
        "compose_file": "docker-compose.yml",
        "description": "Advanced Backend + WebUI",
        "ports": ["8000", "5173"],
    },
    "speaker-recognition": {
        "path": "extras/speaker-recognition",
        "compose_file": "docker-compose.yml",
        "description": "Speaker Recognition Service",
        "ports": ["8085", "5174/8444"],
    },
    "asr-services": {
        "path": "extras/asr-services",
        "compose_file": "docker-compose.yml",
        "description": "Parakeet ASR Service",
        "ports": ["8767"],
    },
    "openmemory-mcp": {
        "path": "extras/openmemory-mcp",
        "compose_file": "docker-compose.yml",
        "description": "OpenMemory MCP Server",
        "ports": ["8765"],
    },
}


def load_config_yml() -> Optional[Dict[str, Any]]:
    """Load config.yml from repository root"""
    config_path = Path(__file__).parent / "config" / "config.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[yellow]⚠️  Warning: Could not parse config/config.yml: {e}[/yellow]")
        return None
    except OSError as e:
        console.print(f"[yellow]⚠️  Warning: Could not read config/config.yml: {e}[/yellow]")
        return None


def check_service_configured(service_name: str) -> bool:
    """Check if service is configured (has .env file)"""
    if service_name not in SERVICES:
        return False

    service = SERVICES[service_name]
    service_path = Path(service["path"])

    # Simple check for .env existence
    return (service_path / ".env").exists()


def _get_service_path(service_name: str) -> Optional[Path]:
    """Validate and return service path"""
    service = SERVICES[service_name]
    service_path = Path(service["path"])

    if not service_path.exists():
        console.print(f"[red]❌ Service directory not found: {service_path}[/red]")
        return None

    compose_file = service_path / service["compose_file"]
    if not compose_file.exists():
        console.print(f"[red]❌ Docker compose file not found: {compose_file}[/red]")
        return None

    return service_path


def _is_obsidian_enabled(service_path: Path) -> bool:
    """Check if Obsidian/Neo4j is enabled via config or env"""
    # Method 1: Check config.yml
    config_data = load_config_yml()
    if config_data:
        memory_config = config_data.get("memory", {})
        obsidian_config = memory_config.get("obsidian", {})
        if obsidian_config.get("enabled", False):
            return True

    # Method 2: Fallback to .env
    env_file = service_path / ".env"
    if env_file.exists():
        env_values = dotenv_values(env_file)
        if env_values.get("OBSIDIAN_ENABLED", "false").lower() == "true":
            return True

    return False


def _get_backend_cmd_args(service_path: Path) -> List[str]:
    """Get backend-specific compose arguments"""
    args = []

    # HTTPS Profile
    caddyfile_path = service_path / "Caddyfile"
    if caddyfile_path.exists() and caddyfile_path.is_file():
        args.extend(["--profile", "https"])

    # Obsidian Profile
    if _is_obsidian_enabled(service_path):
        args.extend(["--profile", "obsidian"])
        console.print("[blue]ℹ️  Starting with Obsidian/Neo4j support[/blue]")

    return args


def _get_speaker_recognition_cmd_args(service_path: Path, command: str) -> List[str]:
    """Get speaker-recognition specific compose arguments"""
    if command not in ["up", "down"]:
        return []

    env_file = service_path / ".env"
    if not env_file.exists():
        return ["up", "-d"] if command == "up" else ["down"]

    env_values = dotenv_values(env_file)
    compute_mode = env_values.get("COMPUTE_MODE", "cpu")
    args = []

    # Profile (cpu/gpu)
    args.extend(["--profile", compute_mode])

    if command == "down":
        args.append("down")
        return args

    # Command is 'up'
    https_enabled = env_values.get("REACT_UI_HTTPS", "false").lower() == "true"

    if https_enabled:
        # HTTPS mode: start all services in profile
        args.extend(["up", "-d"])
    else:
        # HTTP mode: start specific services
        service_suffix = "gpu" if compute_mode == "gpu" else "cpu"
        args.extend(["up", "-d", f"speaker-service-{service_suffix}", "web-ui"])

    return args


def _build_base_cmd(command: str) -> List[str]:
    """Get standard compose command arguments"""
    if command == "up":
        return ["up", "-d"]
    elif command == "down":
        return ["down"]
    elif command == "restart":
        return ["restart"]
    elif command == "status":
        return ["ps"]
    return []


def _construct_docker_cmd(
    service_name: str, service_path: Path, command: str, build: bool
) -> List[str]:
    """Construct the full docker compose command"""
    cmd = ["docker", "compose"]

    # Service-specific logic
    if service_name == "backend":
        cmd.extend(_get_backend_cmd_args(service_path))
        cmd.extend(_build_base_cmd(command))

    elif service_name == "speaker-recognition":
        speaker_args = _get_speaker_recognition_cmd_args(service_path, command)
        if speaker_args:
            cmd.extend(speaker_args)
        else:
            cmd.extend(_build_base_cmd(command))

    else:
        # Standard services
        cmd.extend(_build_base_cmd(command))

    # Add build flag
    if command == "up" and build:
        cmd.append("--build")

    return cmd


def _stream_output(process: subprocess.Popen) -> None:
    """Stream process output with coloring"""
    if process.stdout is None:
        return

    for line in process.stdout:
        line = line.rstrip()
        if not line:
            continue

        if "error" in line.lower() or "failed" in line.lower():
            console.print(f"  [red]{line}[/red]")
        elif any(x in line for x in ["Successfully", "Started", "Created"]):
            console.print(f"  [green]{line}[/green]")
        elif any(x in line for x in ["Building", "Creating"]):
            console.print(f"  [cyan]{line}[/cyan]")
        elif "warning" in line.lower():
            console.print(f"  [yellow]{line}[/yellow]")
        else:
            console.print(f"  [dim]{line}[/dim]")


def run_compose_command(service_name: str, command: str, build: bool = False) -> bool:
    """Run docker compose command for a service"""
    service_path = _get_service_path(service_name)
    if not service_path:
        return False

    cmd = _construct_docker_cmd(service_name, service_path, command, build)

    try:
        # Stream output for builds
        if build and command == "up":
            console.print(f"[dim]Building {service_name} containers...[/dim]")
            with subprocess.Popen(
                cmd,
                cwd=service_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as process:
                _stream_output(process)
                process.wait()

            if process.returncode != 0:
                console.print(f"\n[red]❌ Build failed for {service_name}[/red]")
                return False
            return True

        # Run silently for other commands
        result = subprocess.run(
            cmd,
            cwd=service_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        if result.returncode == 0:
            return True

        console.print(f"[red]❌ Command failed[/red]")
        if result.stderr:
            console.print("[red]Error output:[/red]")
            for line in result.stderr.splitlines():
                console.print(f"  [dim]{line}[/dim]")
        return False

    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Command timed out after 2 minutes for {service_name}[/red]")
        return False
    except OSError as e:
        console.print(f"[red]❌ Error executing command: {e}[/red]")
        return False


def start_services(services: List[str], build: bool = False) -> None:
    """Start specified services"""
    console.print(f"🚀 [bold]Starting {len(services)} services...[/bold]")

    success_count = 0
    for service_name in services:
        if service_name not in SERVICES:
            console.print(f"[red]❌ Unknown service: {service_name}[/red]")
            continue

        if not check_service_configured(service_name):
            console.print(f"[yellow]⚠️  {service_name} not configured, skipping[/yellow]")
            continue

        console.print(f"\n🔧 Starting {service_name}...")
        if run_compose_command(service_name, "up", build):
            console.print(f"[green]✅ {service_name} started[/green]")
            success_count += 1
        else:
            console.print(f"[red]❌ Failed to start {service_name}[/red]")

    console.print(
        f"\n[green]🎉 {success_count}/{len(services)} services started successfully[/green]"
    )


def stop_services(services: List[str]) -> None:
    """Stop specified services"""
    console.print(f"🛑 [bold]Stopping {len(services)} services...[/bold]")

    success_count = 0
    for service_name in services:
        if service_name not in SERVICES:
            console.print(f"[red]❌ Unknown service: {service_name}[/red]")
            continue

        console.print(f"\n🔧 Stopping {service_name}...")
        if run_compose_command(service_name, "down"):
            console.print(f"[green]✅ {service_name} stopped[/green]")
            success_count += 1
        else:
            console.print(f"[red]❌ Failed to stop {service_name}[/red]")

    console.print(
        f"\n[green]🎉 {success_count}/{len(services)} services stopped successfully[/green]"
    )


def restart_services(services: List[str], recreate: bool = False) -> None:
    """Restart specified services"""
    console.print(f"🔄 [bold]Restarting {len(services)} services...[/bold]")

    if recreate:
        console.print(
        "[dim]Using down + up to recreate containers (fixes WSL2 bind mount issues)[/dim]\n"
        )
    else:
        console.print(
        "[dim]Quick restart (use --recreate to fix bind mount issues)[/dim]\n"
        )

    success_count = 0
    for service_name in services:
        if service_name not in SERVICES:
            console.print(f"[red]❌ Unknown service: {service_name}[/red]")
            continue

        if not check_service_configured(service_name):
            console.print(f"[yellow]⚠️  {service_name} not configured, skipping[/yellow]")
            continue

        console.print(f"\n🔧 Restarting {service_name}...")

        if recreate:
            # Full recreation: down + up
            if not run_compose_command(service_name, "down"):
                console.print(f"[red]❌ Failed to stop {service_name}[/red]")
                continue

            if run_compose_command(service_name, "up"):
                console.print(f"[green]✅ {service_name} restarted[/green]")
                success_count += 1
            else:
                console.print(f"[red]❌ Failed to start {service_name}[/red]")
        else:
            # Quick restart
            if run_compose_command(service_name, "restart"):
                console.print(f"[green]✅ {service_name} restarted[/green]")
                success_count += 1
            else:
                console.print(f"[red]❌ Failed to restart {service_name}[/red]")

    console.print(
        f"\n[green]🎉 {success_count}/{len(services)} services restarted successfully[/green]"
    )


def show_status() -> None:
    """Show status of all services"""
    console.print("📊 [bold]Service Status:[/bold]\n")

    table = Table()
    table.add_column("Service", style="cyan")
    table.add_column("Configured", justify="center")
    table.add_column("Description", style="dim")
    table.add_column("Ports", style="green")

    for service_name, service_info in SERVICES.items():
        configured = "✅" if check_service_configured(service_name) else "❌"
        ports = ", ".join(service_info["ports"])
        table.add_row(service_name, configured, service_info["description"], ports)

    console.print(table)

    console.print(
        "\n💡 [dim]Use 'python services.py start --all' to start all configured services[/dim]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronicle Service Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument(
        "services",
        nargs="*",
        help="Services to start: backend, speaker-recognition, asr-services, openmemory-mcp (or use --all)",
    )
    start_parser.add_argument(
        "--all", action="store_true", help="Start all configured services"
    )
    start_parser.add_argument(
        "--build", action="store_true", help="Build images before starting"
    )

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop services")
    stop_parser.add_argument(
        "services",
        nargs="*",
        help="Services to stop: backend, speaker-recognition, asr-services, openmemory-mcp (or use --all)",
    )
    stop_parser.add_argument(
        "--all", action="store_true", help="Stop all services"
    )

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart services")
    restart_parser.add_argument(
        "services",
        nargs="*",
        help="Services to restart: backend, speaker-recognition, asr-services, openmemory-mcp (or use --all)",
    )
    restart_parser.add_argument(
        "--all", action="store_true", help="Restart all services"
    )
    restart_parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate containers (down + up) instead of quick restart - fixes WSL2 bind mount issues",
    )

    # Status command
    subparsers.add_parser("status", help="Show service status")

    args = parser.parse_args()

    if not args.command:
        show_status()
        return

    if args.command == "status":
        show_status()
        return

    # Handle common logic for start/stop/restart
    services_to_process: List[str] = []

    if args.all:
        services_to_process = [s for s in SERVICES.keys() if check_service_configured(s)]
    elif args.services:
        # Validate service names
        invalid_services = [s for s in args.services if s not in SERVICES]
        if invalid_services:
            console.print(
                f"[red]❌ Invalid service names: {', '.join(invalid_services)}[/red]"
            )
            console.print(f"Available services: {', '.join(SERVICES.keys())}")
            return
        services_to_process = args.services
    else:
        console.print(
            "[red]❌ No services specified. Use --all or specify service names.[/red]"
        )
        return

    if args.command == "start":
        start_services(services_to_process, args.build)
    elif args.command == "stop":
        stop_services(services_to_process)
    elif args.command == "restart":
        restart_services(services_to_process, recreate=args.recreate)


if __name__ == "__main__":
    main()
