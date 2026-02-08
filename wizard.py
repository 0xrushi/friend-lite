#!/usr/bin/env python3
"""
Chronicle Root Setup Orchestrator
Handles service selection and delegation only - no configuration duplication
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from dotenv import get_key
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# Type definitions
ServiceConfig = Dict[str, Any]
ServiceGroup = Dict[str, ServiceConfig]
ServicesData = Dict[str, ServiceGroup]

SERVICES: ServicesData = {
    "backend": {
        "advanced": {
            "path": "backends/advanced",
            "cmd": [
                "uv",
                "run",
                "--with-requirements",
                "../../setup-requirements.txt",
                "python",
                "init.py",
            ],
            "description": "Advanced Backend with full feature set",
            "required": True,
        }
    },
    "extras": {
        "speaker-recognition": {
            "path": "extras/speaker-recognition",
            "cmd": [
                "uv",
                "run",
                "--with-requirements",
                "../../setup-requirements.txt",
                "python",
                "init.py",
            ],
            "description": "Speaker identification and enrollment",
        },
        "asr-services": {
            "path": "extras/asr-services",
            "cmd": [
                "uv",
                "run",
                "--with-requirements",
                "../../setup-requirements.txt",
                "python",
                "init.py",
            ],
            "description": "Offline speech-to-text (Parakeet)",
        },
        "openmemory-mcp": {
            "path": "extras/openmemory-mcp",
            "cmd": ["./setup.sh"],
            "description": "OpenMemory MCP server",
        },
    },
}


def read_env_value(env_file_path: Union[str, Path], key: str) -> Optional[str]:
    """Read a value from an .env file using python-dotenv"""
    env_path = Path(env_file_path)
    if not env_path.exists():
        return None

    value = get_key(str(env_path), key)
    return value if value else None


def is_placeholder(value: Optional[str], *placeholder_variants: str) -> bool:
    """
    Check if a value is a placeholder or empty.
    """
    if not value:
        return True

    normalized_value = value.replace("-", "_").lower()

    for placeholder in placeholder_variants:
        normalized_placeholder = placeholder.replace("-", "_").lower()
        if normalized_value == normalized_placeholder:
            return True

    return False


def check_service_exists(
    service_name: str, service_config: ServiceConfig
) -> Tuple[bool, str]:
    """Check if service directory and script exist"""
    service_path = Path(service_config["path"])
    if not service_path.exists():
        return False, f"Directory {service_path} does not exist"

    # For services with Python init scripts
    if service_name in ["advanced", "speaker-recognition", "asr-services"]:
        script_path = service_path / "init.py"
        if not script_path.exists():
            return False, f"Script {script_path} does not exist"
    else:
        # For other extras (shell scripts)
        script_path = service_path / "setup.sh"
        if not script_path.exists():
            return (
                False,
                f"Script {script_path} does not exist (will be created in Phase 2)",
            )

    return True, "OK"


def _ensure_hf_token() -> Optional[str]:
    """Ensure Hugging Face token is available for speaker-recognition"""
    speaker_env_path = "extras/speaker-recognition/.env"
    hf_token = read_env_value(speaker_env_path, "HF_TOKEN")

    if not hf_token or is_placeholder(
        hf_token,
        "your_huggingface_token_here",
        "your-huggingface-token-here",
        "hf_xxxxx",
    ):
        console.print(
            "\n[red][ERROR][/red] HF_TOKEN is required for speaker-recognition service"
        )
        console.print(
            "[yellow]Speaker recognition requires a Hugging Face token to download models[/yellow]"
        )
        console.print("Get your token from: https://huggingface.co/settings/tokens")
        console.print()

        try:
            hf_token_input = console.input("[cyan]Enter your HF_TOKEN[/cyan]: ").strip()
            if not hf_token_input or is_placeholder(
                hf_token_input, "your_huggingface_token_here", "hf_xxxxx"
            ):
                console.print("[red][ERROR][/red] Invalid HF_TOKEN provided.")
                return None
            return hf_token_input
        except EOFError:
            return None

    return hf_token


def _configure_advanced_backend(
    cmd: List[str],
    selected_services: List[str],
    https_enabled: bool,
    server_ip: Optional[str],
    obsidian_enabled: bool,
    neo4j_password: Optional[str],
) -> List[str]:
    """Configure arguments for advanced backend"""
    new_cmd = cmd.copy()
    if "speaker-recognition" in selected_services:
        new_cmd.extend(["--speaker-service-url", "http://speaker-service:8085"])
    if "asr-services" in selected_services:
        new_cmd.extend(["--parakeet-asr-url", "http://host.docker.internal:8767"])

    if https_enabled and server_ip:
        new_cmd.extend(["--enable-https", "--server-ip", server_ip])

    if obsidian_enabled and neo4j_password:
        new_cmd.extend(["--enable-obsidian", "--neo4j-password", neo4j_password])

    return new_cmd


def _configure_speaker_recognition(
    cmd: List[str], https_enabled: bool, server_ip: Optional[str]
) -> Optional[List[str]]:
    """Configure arguments for speaker recognition"""
    new_cmd = cmd.copy()

    if https_enabled and server_ip:
        new_cmd.extend(["--enable-https", "--server-ip", server_ip])

    # HF Token
    hf_token = _ensure_hf_token()
    if not hf_token:
        return None
    new_cmd.extend(["--hf-token", hf_token])
    console.print("[green][SUCCESS][/green] HF_TOKEN configured")

    # Deepgram Key Reuse
    backend_env = "backends/advanced/.env"
    deepgram_key = read_env_value(backend_env, "DEEPGRAM_API_KEY")
    if deepgram_key and not is_placeholder(
        deepgram_key, "your_deepgram_api_key_here"
    ):
        new_cmd.extend(["--deepgram-api-key", deepgram_key])
        console.print(
            "[blue][INFO][/blue] Found existing DEEPGRAM_API_KEY from backend config, reusing"
        )

    # Compute Mode Reuse
    speaker_env = "extras/speaker-recognition/.env"
    compute_mode = read_env_value(speaker_env, "COMPUTE_MODE")
    if compute_mode in ["cpu", "gpu"]:
        new_cmd.extend(["--compute-mode", compute_mode])
        console.print(
            f"[blue][INFO][/blue] Found existing COMPUTE_MODE ({compute_mode}), reusing"
        )

    return new_cmd


def _configure_asr_services(cmd: List[str]) -> List[str]:
    """Configure arguments for ASR services"""
    new_cmd = cmd.copy()
    speaker_env = "extras/speaker-recognition/.env"
    cuda_version = read_env_value(speaker_env, "PYTORCH_CUDA_VERSION")
    if cuda_version and cuda_version in ["cu121", "cu126", "cu128"]:
        new_cmd.extend(["--pytorch-cuda-version", cuda_version])
        console.print(
            f"[blue][INFO][/blue] Found existing PYTORCH_CUDA_VERSION ({cuda_version}) from speaker-recognition, reusing"
        )
    return new_cmd


def _configure_openmemory_mcp(cmd: List[str]) -> List[str]:
    """Configure arguments for OpenMemory MCP"""
    new_cmd = cmd.copy()
    backend_env = "backends/advanced/.env"
    openai_key = read_env_value(backend_env, "OPENAI_API_KEY")
    if openai_key and not is_placeholder(
        openai_key, "your_openai_api_key_here", "your_openai_key_here"
    ):
        new_cmd.extend(["--openai-api-key", openai_key])
        console.print(
            "[blue][INFO][/blue] Found existing OPENAI_API_KEY from backend config, reusing"
        )
    return new_cmd


def run_service_setup(
    service_name: str,
    selected_services: List[str],
    https_enabled: bool = False,
    server_ip: Optional[str] = None,
    obsidian_enabled: bool = False,
    neo4j_password: Optional[str] = None,
) -> bool:
    """Execute individual service setup script"""
    console.print(f"\n🔧 [bold]Setting up {service_name}...[/bold]")

    # Identify service config
    if service_name == "advanced":
        service = SERVICES["backend"][service_name]
        cmd = _configure_advanced_backend(
            service["cmd"],
            selected_services,
            https_enabled,
            server_ip,
            obsidian_enabled,
            neo4j_password,
        )
    else:
        service = SERVICES["extras"][service_name]
        cmd = service["cmd"]

        if service_name == "speaker-recognition":
            result_cmd = _configure_speaker_recognition(cmd, https_enabled, server_ip)
            if result_cmd is None:
                return False
            cmd = result_cmd
        elif service_name == "asr-services":
            cmd = _configure_asr_services(cmd)
        elif service_name == "openmemory-mcp":
            cmd = _configure_openmemory_mcp(cmd)

    exists, msg = check_service_exists(service_name, service)
    if not exists:
        console.print(f"❌ {service_name} setup failed: {msg}")
        return False

    try:
        subprocess.run(cmd, cwd=service["path"], check=True, timeout=300)
        console.print(f"✅ {service_name} setup completed")
        return True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ) as e:
        console.print(f"❌ {service_name} setup failed: {e}")
        return False
    except Exception as e:
        console.print(f"❌ {service_name} setup failed (unexpected): {e}")
        return False


def select_services() -> List[str]:
    """Let user select which services to setup"""
    console.print("🚀 [bold cyan]Chronicle Service Setup[/bold cyan]")
    console.print("Select which services to configure:\n")

    selected = []

    # Backend
    console.print("📱 [bold]Backend (Required):[/bold]")
    console.print("  ✅ Advanced Backend - Full AI features")
    selected.append("advanced")

    # Extras
    console.print("\n🔧 [bold]Optional Services:[/bold]")
    for service_name, service_config in SERVICES["extras"].items():
        exists, msg = check_service_exists(service_name, service_config)
        if not exists:
            console.print(f"  ⏸️  {service_config['description']} - [dim]{msg}[/dim]")
            continue

        try:
            if Confirm.ask(f"  Setup {service_config['description']}?", default=False):
                selected.append(service_name)
        except EOFError:
            pass

    return selected


def cleanup_unselected_services(selected_services: List[str]) -> None:
    """Backup and remove .env files from services that weren't selected"""
    all_services = list(SERVICES["backend"].keys()) + list(SERVICES["extras"].keys())

    for service_name in all_services:
        if service_name not in selected_services:
            if service_name == "advanced":
                service_path = Path(SERVICES["backend"][service_name]["path"])
            else:
                service_path = Path(SERVICES["extras"][service_name]["path"])

            env_file = service_path / ".env"
            if env_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = service_path / f".env.backup.{timestamp}.unselected"
                env_file.rename(backup_file)
                console.print(
                    f"🧹 [dim]Backed up {service_name} config to {backup_file.name}[/dim]"
                )


def setup_https(selected_services: List[str]) -> Tuple[bool, Optional[str]]:
    """Prompt and configure HTTPS settings"""
    # Check if we have services that benefit from HTTPS
    https_services = {"advanced", "speaker-recognition"}
    needs_https = bool(https_services.intersection(selected_services))

    if not needs_https:
        return False, None

    console.print("\n🔒 [bold cyan]HTTPS Configuration[/bold cyan]")
    try:
        if not Confirm.ask("Enable HTTPS for selected services?", default=False):
            return False, None
    except EOFError:
        return False, None

    console.print("\n[blue][INFO][/blue] For distributed deployments, use your Tailscale IP")
    console.print("Examples: localhost, 100.64.1.2, your-domain.com")

    backend_env_path = "backends/advanced/.env"
    existing_ip = read_env_value(backend_env_path, "SERVER_IP")
    default_value = (
        existing_ip
        if existing_ip and existing_ip not in ["localhost", "your-server-ip-here"]
        else "localhost"
    )

    prompt_text = f"Server IP/Domain [{default_value}]"

    while True:
        try:
            server_ip = console.input(f"{prompt_text}: ").strip()
            if not server_ip:
                server_ip = default_value
            break
        except EOFError:
            server_ip = default_value
            break

    console.print(f"[green]✅[/green] HTTPS configured for: {server_ip}")
    return True, server_ip


def setup_obsidian(selected_services: List[str]) -> Tuple[bool, Optional[str]]:
    """Prompt and configure Obsidian/Neo4j settings"""
    if "advanced" not in selected_services:
        return False, None

    console.print("\n🗂️ [bold cyan]Obsidian/Neo4j Integration[/bold cyan]")
    try:
        if not Confirm.ask("Enable Obsidian/Neo4j integration?", default=False):
            return False, None
    except EOFError:
        return False, None

    console.print("[blue][INFO][/blue] Neo4j will be configured for graph-based memory storage\n")

    while True:
        try:
            password = (
                console.input("Neo4j password (min 8 chars) [default: neo4jpassword]: ").strip()
                or "neo4jpassword"
            )
            if len(password) >= 8:
                return True, password
            console.print("[yellow][WARNING][/yellow] Password must be at least 8 characters")
        except EOFError:
            return True, "neo4jpassword"


def show_service_status() -> None:
    """Show which services are available"""
    console.print("\n📋 [bold]Service Status:[/bold]")

    # Check backend
    exists, msg = check_service_exists("advanced", SERVICES["backend"]["advanced"])
    status = "✅" if exists else "❌"
    console.print(f"  {status} Advanced Backend - {msg}")

    # Check extras
    for service_name, service_config in SERVICES["extras"].items():
        exists, msg = check_service_exists(service_name, service_config)
        status = "✅" if exists else "⏸️"
        console.print(f"  {status} {service_config['description']} - {msg}")


def setup_git_hooks() -> None:
    """Setup pre-commit hooks for development"""
    console.print("\n🔧 [bold]Setting up development environment...[/bold]")

    try:
        subprocess.run(
            ["pip", "install", "pre-commit"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        result = subprocess.run(
            ["pre-commit", "install", "--hook-type", "pre-push"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            console.print(
                "✅ [green]Git hooks installed (tests will run before push)[/green]"
            )
        else:
            console.print("⚠️  [yellow]Could not install git hooks (optional)[/yellow]")

        subprocess.run(
            ["pre-commit", "install", "--hook-type", "pre-commit"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    except Exception as e:
        console.print(f"⚠️  [yellow]Could not setup git hooks: {e} (optional)[/yellow]")


def setup_config_file() -> None:
    """Setup config/config.yml from template if it doesn't exist"""
    config_file = Path("config/config.yml")
    config_template = Path("config/config.yml.template")

    if not config_file.exists():
        if config_template.exists():
            config_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(config_template, config_file)
            console.print("✅ [green]Created config/config.yml from template[/green]")
        else:
            console.print(
                "⚠️  [yellow]config/config.yml.template not found, skipping config setup[/yellow]"
            )
    else:
        console.print(
            "ℹ️  [blue]config/config.yml already exists, keeping existing configuration[/blue]"
        )


def main() -> None:
    """Main orchestration logic"""
    console.print("🎉 [bold green]Welcome to Chronicle![/bold green]\n")

    setup_config_file()
    setup_git_hooks()
    show_service_status()

    selected_services = select_services()
    if not selected_services:
        console.print("[yellow]No services selected. Exiting.[/yellow]")
        return

    https_enabled, server_ip = setup_https(selected_services)
    obsidian_enabled, neo4j_password = setup_obsidian(selected_services)

    console.print(f"\n📋 [bold]Setting up {len(selected_services)} services...[/bold]")
    cleanup_unselected_services(selected_services)

    success_count = 0
    failed_services = []

    for service in selected_services:
        if run_service_setup(
            service,
            selected_services,
            https_enabled,
            server_ip,
            obsidian_enabled,
            neo4j_password,
        ):
            success_count += 1
        else:
            failed_services.append(service)

    # Check for Obsidian configuration via config.yml for final messaging
    config_obsidian_enabled = False
    if "advanced" in selected_services and "advanced" not in failed_services:
        config_yml_path = Path("config/config.yml")
        if config_yml_path.exists():
            try:
                with open(config_yml_path, "r") as f:
                    config_data = yaml.safe_load(f)
                    obsidian_config = config_data.get("memory", {}).get("obsidian", {})
                    config_obsidian_enabled = obsidian_config.get("enabled", False)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not read config.yml: {e}[/yellow]")

    console.print(f"\n🎊 [bold green]Setup Complete![/bold green]")
    console.print(
        f"✅ {success_count}/{len(selected_services)} services configured successfully"
    )

    if failed_services:
        console.print(f"❌ Failed services: {', '.join(failed_services)}")

    if config_obsidian_enabled or obsidian_enabled:
        console.print(f"\n📚 [bold cyan]Obsidian Integration Detected[/bold cyan]")
        console.print(
            "   Neo4j will be automatically started with the 'obsidian' profile"
        )
        console.print("   when you start the backend service.")

    # Next Steps messaging
    console.print("\n📖 [bold]Next Steps:[/bold]")
    console.print("")
    console.print("📝 [bold cyan]Configuration Files Updated:[/bold cyan]")
    console.print("   • [green].env files[/green] - API keys and service URLs")
    console.print(
        "   • [green]config.yml[/green] - Model definitions and memory provider settings"
    )
    console.print("")
    console.print("1. Setup development environment (git hooks, testing):")
    console.print("   [cyan]make setup-dev[/cyan]")
    console.print("")
    console.print("2. Start all configured services:")
    console.print(
        "   [cyan]uv run --with-requirements setup-requirements.txt python services.py start --all --build[/cyan]"
    )
    console.print("")


if __name__ == "__main__":
    main()
