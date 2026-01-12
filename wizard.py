#!/usr/bin/env python3
"""
Chronicle Root Setup Orchestrator
Handles service selection and delegation only - no configuration duplication
"""

import getpass
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import get_key
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

def read_env_value(env_file_path, key):
    """Read a value from an .env file using python-dotenv"""
    env_path = Path(env_file_path)
    if not env_path.exists():
        return None

    value = get_key(str(env_path), key)
    # get_key returns None if key doesn't exist or value is empty
    return value if value else None

def is_placeholder(value, *placeholder_variants):
    """
    Check if a value is a placeholder by normalizing both the value and placeholders.
    Treats 'your-key-here' and 'your_key_here' as equivalent.

    Args:
        value: The value to check
        placeholder_variants: One or more placeholder strings to check against

    Returns:
        True if value matches any placeholder variant (after normalization)
    """
    if not value:
        return True

    # Normalize by replacing hyphens with underscores
    normalized_value = value.replace('-', '_').lower()

    for placeholder in placeholder_variants:
        normalized_placeholder = placeholder.replace('-', '_').lower()
        if normalized_value == normalized_placeholder:
            return True

    return False

SERVICES = {
    'backend': {
        'advanced': {
            'path': 'backends/advanced',
            'cmd': ['uv', 'run', '--with-requirements', '../../setup-requirements.txt', 'python', 'init.py'],
            'description': 'Advanced AI backend with full feature set',
            'required': True
        }
    },
    'extras': {
        'speaker-recognition': {
            'path': 'extras/speaker-recognition',
            'cmd': ['uv', 'run', '--with-requirements', '../../setup-requirements.txt', 'python', 'init.py'],
            'description': 'Speaker identification and enrollment'
        },
        'asr-services': {
            'path': 'extras/asr-services',
            'cmd': ['uv', 'run', '--with-requirements', '../../setup-requirements.txt', 'python', 'init.py'],
            'description': 'Offline speech-to-text (Parakeet)'
        },
        'openmemory-mcp': {
            'path': 'extras/openmemory-mcp',
            'cmd': ['./setup.sh'],
            'description': 'OpenMemory MCP server'
        }
    }
}

# Plugin configuration registry
# Plugins are lightweight integrations that extend Chronicle functionality
# They are configured during wizard setup and stored in config/plugins.yml
#
# Access Levels (when plugins execute):
#   - transcript: Fires when new transcript segment arrives
#   - conversation: Fires when conversation completes
#   - memory: Fires after memory extraction
#
# Trigger Types (how plugins decide to execute):
#   - wake_word: Only if transcript starts with specified wake word
#   - always: Execute on every invocation at this access level
#   - conditional: Custom condition checking (future)
PLUGINS = {
    'homeassistant': {
        'name': 'Home Assistant',
        'description': 'Control Home Assistant devices via natural language with wake word',
        'enabled_by_default': False,
        'requires_tailscale': True,  # Requires Tailscale for remote HA access
        'access_level': 'streaming_transcript',  # When to trigger
        'trigger_type': 'wake_word',   # How to trigger
        'config': {
            'ha_url': {
                'prompt': 'Home Assistant URL',
                'default': 'http://localhost:8123',
                'type': 'url',
                'help': 'The URL of your Home Assistant instance (e.g., http://100.99.62.5:8123)'
            },
            'ha_token': {
                'prompt': 'Long-Lived Access Token',
                'type': 'password',
                'help': 'Create at: Home Assistant > Profile > Long-Lived Access Tokens'
            },
            'wake_words': {
                'prompt': 'Wake words for HA commands (comma-separated)',
                'default': 'hey vivi, hey jarvis',
                'type': 'text',
                'help': 'Say these words before commands. Use comma-separated list for multiple (e.g., "hey vivi, hey jarvis")'
            }
        }
    }
    # Future plugin examples:
    # 'sentiment_analyzer': {
    #     'name': 'Sentiment Analyzer',
    #     'access_level': 'conversation',
    #     'trigger_type': 'always',
    #     ...
    # },
    # 'memory_enricher': {
    #     'name': 'Memory Enricher',
    #     'access_level': 'memory',
    #     'trigger_type': 'always',
    #     ...
    # }
}

def check_service_exists(service_name, service_config):
    """Check if service directory and script exist"""
    service_path = Path(service_config['path'])
    if not service_path.exists():
        return False, f"Directory {service_path} does not exist"

    # For services with Python init scripts, check if init.py exists
    if service_name in ['advanced', 'speaker-recognition', 'asr-services']:
        script_path = service_path / 'init.py'
        if not script_path.exists():
            return False, f"Script {script_path} does not exist"
    else:
        # For other extras, check if setup.sh exists
        script_path = service_path / 'setup.sh'
        if not script_path.exists():
            return False, f"Script {script_path} does not exist (will be created in Phase 2)"

    return True, "OK"

def select_services():
    """Let user select which services to setup"""
    console.print("🚀 [bold cyan]Chronicle Service Setup[/bold cyan]")
    console.print("Select which services to configure:\n")
    
    selected = []
    
    # Backend is required
    console.print("📱 [bold]Backend (Required):[/bold]")
    console.print("  ✅ Advanced Backend - Full AI features")
    selected.append('advanced')
    
    # Optional extras
    console.print("\n🔧 [bold]Optional Services:[/bold]")
    for service_name, service_config in SERVICES['extras'].items():
        # Check if service exists
        exists, msg = check_service_exists(service_name, service_config)
        if not exists:
            console.print(f"  ⏸️  {service_config['description']} - [dim]{msg}[/dim]")
            continue
        
        try:
            enable_service = Confirm.ask(f"  Setup {service_config['description']}?", default=False)
        except EOFError:
            console.print("Using default: No")
            enable_service = False
            
        if enable_service:
            selected.append(service_name)
    
    return selected

def cleanup_unselected_services(selected_services):
    """Backup and remove .env files from services that weren't selected"""
    
    all_services = list(SERVICES['backend'].keys()) + list(SERVICES['extras'].keys())
    
    for service_name in all_services:
        if service_name not in selected_services:
            if service_name == 'advanced':
                service_path = Path(SERVICES['backend'][service_name]['path'])
            else:
                service_path = Path(SERVICES['extras'][service_name]['path'])
            
            env_file = service_path / '.env'
            if env_file.exists():
                # Create backup with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = service_path / f'.env.backup.{timestamp}.unselected'
                env_file.rename(backup_file)
                console.print(f"🧹 [dim]Backed up {service_name} configuration to {backup_file.name} (service not selected)[/dim]")

def run_service_setup(service_name, selected_services, https_enabled=False, server_ip=None,
                     obsidian_enabled=False, neo4j_password=None, ts_authkey=None, hf_token=None,
                     transcription_provider='deepgram'):
    """Execute individual service setup script"""
    if service_name == 'advanced':
        service = SERVICES['backend'][service_name]

        # For advanced backend, pass URLs of other selected services and HTTPS config
        cmd = service['cmd'].copy()
        if 'speaker-recognition' in selected_services:
            cmd.extend(['--speaker-service-url', 'http://speaker-service:8085'])
        if 'asr-services' in selected_services:
            cmd.extend(['--parakeet-asr-url', 'http://host.docker.internal:8767'])

        # Pass transcription provider choice from wizard
        if transcription_provider:
            cmd.extend(['--transcription-provider', transcription_provider])

        # Add HTTPS configuration
        if https_enabled and server_ip:
            cmd.extend(['--enable-https', '--server-ip', server_ip])

        # Add Obsidian configuration
        if obsidian_enabled and neo4j_password:
            cmd.extend(['--enable-obsidian', '--neo4j-password', neo4j_password])

        # Add Tailscale configuration
        if ts_authkey:
            cmd.extend(['--ts-authkey', ts_authkey])

    else:
        service = SERVICES['extras'][service_name]
        cmd = service['cmd'].copy()
        
        # Add HTTPS configuration for services that support it
        if service_name == 'speaker-recognition' and https_enabled and server_ip:
            cmd.extend(['--enable-https', '--server-ip', server_ip])

        # For speaker-recognition, pass HF_TOKEN from centralized configuration
        if service_name == 'speaker-recognition':
            # Define the speaker env path
            speaker_env_path = 'extras/speaker-recognition/.env'

            # HF Token should have been provided via setup_hf_token_if_needed()
            if hf_token:
                cmd.extend(['--hf-token', hf_token])
            else:
                console.print("[yellow][WARNING][/yellow] No HF_TOKEN provided - speaker recognition may fail to download models")

            # Pass Deepgram API key from backend if available
            backend_env_path = 'backends/advanced/.env'
            deepgram_key = read_env_value(backend_env_path, 'DEEPGRAM_API_KEY')
            if deepgram_key and not is_placeholder(deepgram_key, 'your_deepgram_api_key_here', 'your-deepgram-api-key-here'):
                cmd.extend(['--deepgram-api-key', deepgram_key])
                console.print("[blue][INFO][/blue] Found existing DEEPGRAM_API_KEY from backend config, reusing")

            # Pass compute mode from existing .env if available
            compute_mode = read_env_value(speaker_env_path, 'COMPUTE_MODE')
            if compute_mode in ['cpu', 'gpu']:
                cmd.extend(['--compute-mode', compute_mode])
                console.print(f"[blue][INFO][/blue] Found existing COMPUTE_MODE ({compute_mode}), reusing")
        
        # For asr-services, try to reuse PYTORCH_CUDA_VERSION from speaker-recognition
        if service_name == 'asr-services':
            speaker_env_path = 'extras/speaker-recognition/.env'
            cuda_version = read_env_value(speaker_env_path, 'PYTORCH_CUDA_VERSION')
            if cuda_version and cuda_version in ['cu121', 'cu126', 'cu128']:
                cmd.extend(['--pytorch-cuda-version', cuda_version])
                console.print(f"[blue][INFO][/blue] Found existing PYTORCH_CUDA_VERSION ({cuda_version}) from speaker-recognition, reusing")

        # For openmemory-mcp, try to pass OpenAI API key from backend if available
        if service_name == 'openmemory-mcp':
            backend_env_path = 'backends/advanced/.env'
            openai_key = read_env_value(backend_env_path, 'OPENAI_API_KEY')
            if openai_key and not is_placeholder(openai_key, 'your_openai_api_key_here', 'your-openai-api-key-here', 'your_openai_key_here', 'your-openai-key-here'):
                cmd.extend(['--openai-api-key', openai_key])
                console.print("[blue][INFO][/blue] Found existing OPENAI_API_KEY from backend config, reusing")
    
    console.print(f"\n🔧 [bold]Setting up {service_name}...[/bold]")
    
    # Check if service exists before running
    exists, msg = check_service_exists(service_name, service)
    if not exists:
        console.print(f"❌ {service_name} setup failed: {msg}")
        return False
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=service['path'],
            check=True,
            timeout=300  # 5 minute timeout for service setup
        )
        
        console.print(f"✅ {service_name} setup completed")
        return True
            
    except FileNotFoundError as e:
        console.print(f"❌ {service_name} setup failed: {e}")
        return False
    except subprocess.TimeoutExpired as e:
        console.print(f"❌ {service_name} setup timed out after {e.timeout} seconds")
        return False
    except subprocess.CalledProcessError as e:
        console.print(f"❌ {service_name} setup failed with exit code {e.returncode}")
        return False
    except Exception as e:
        console.print(f"❌ {service_name} setup failed: {e}")
        return False

def show_service_status():
    """Show which services are available"""
    console.print("\n📋 [bold]Service Status:[/bold]")
    
    # Check backend
    exists, msg = check_service_exists('advanced', SERVICES['backend']['advanced'])
    status = "✅" if exists else "❌"
    console.print(f"  {status} Advanced Backend - {msg}")
    
    # Check extras
    for service_name, service_config in SERVICES['extras'].items():
        exists, msg = check_service_exists(service_name, service_config)
        status = "✅" if exists else "⏸️"
        console.print(f"  {status} {service_config['description']} - {msg}")

def prompt_value(prompt_text, default=""):
    """Prompt user for a value with a default"""
    if default:
        display_prompt = f"{prompt_text} [{default}]"
    else:
        display_prompt = prompt_text

    try:
        value = console.input(f"[cyan]{display_prompt}:[/cyan] ").strip()
        return value if value else default
    except EOFError:
        return default

def prompt_password(prompt_text):
    """Prompt user for a password (hidden input)"""
    try:
        return getpass.getpass(f"{prompt_text}: ")
    except (EOFError, KeyboardInterrupt):
        return ""

def mask_value(value, show_chars=5):
    """Mask a value showing only first and last few characters"""
    if not value or len(value) <= show_chars * 2:
        return value

    # Remove quotes if present
    value_clean = value.strip("'\"")

    return f"{value_clean[:show_chars]}{'*' * min(15, len(value_clean) - show_chars * 2)}{value_clean[-show_chars:]}"

def read_plugin_config_value(plugin_id, config_key):
    """Read a value from existing plugins.yml file"""
    plugins_yml_path = Path('config/plugins.yml')
    if not plugins_yml_path.exists():
        return None

    try:
        with open(plugins_yml_path, 'r') as f:
            plugins_data = yaml.safe_load(f)

        if not plugins_data or 'plugins' not in plugins_data:
            return None

        plugin_config = plugins_data['plugins'].get(plugin_id, {})
        return plugin_config.get(config_key)
    except Exception:
        return None

def prompt_with_existing_masked(prompt_text, existing_value, placeholders=None, is_password=False, default=""):
    """
    Prompt for a value, showing masked existing value if present.

    Args:
        prompt_text: The prompt to display
        existing_value: Existing value from config (or None)
        placeholders: List of placeholder values to treat as "not set"
        is_password: Whether to use password input (hidden)
        default: Default value if no existing value

    Returns:
        User input value, existing value if reused, or default
    """
    placeholders = placeholders or []

    # Check if existing value is valid (not empty and not a placeholder)
    has_valid_existing = existing_value and existing_value not in placeholders

    if has_valid_existing:
        # Show masked value with option to reuse
        if is_password:
            masked = mask_value(existing_value)
            display_prompt = f"{prompt_text} ({masked}) [press Enter to reuse, or enter new]"
        else:
            display_prompt = f"{prompt_text} ({existing_value}) [press Enter to reuse, or enter new]"

        if is_password:
            user_input = prompt_password(display_prompt)
        else:
            user_input = prompt_value(display_prompt, "")

        # If user pressed Enter (empty input), reuse existing value
        return user_input if user_input else existing_value
    else:
        # No existing value, prompt normally
        if is_password:
            return prompt_password(prompt_text)
        else:
            return prompt_value(prompt_text, default)

def select_plugins():
    """Interactive plugin selection and configuration"""
    console.print("\n🔌 [bold cyan]Plugin Configuration[/bold cyan]")
    console.print("Chronicle supports plugins for extended functionality.\n")

    selected_plugins = {}

    for plugin_id, plugin_meta in PLUGINS.items():
        # Show plugin description with access level and trigger type
        console.print(f"[bold]{plugin_meta['name']}[/bold]")
        console.print(f"  {plugin_meta['description']}")
        console.print(f"  Access Level: [cyan]{plugin_meta['access_level']}[/cyan]")
        console.print(f"  Trigger Type: [cyan]{plugin_meta['trigger_type']}[/cyan]\n")

        try:
            enable = Confirm.ask(
                f"  Enable {plugin_meta['name']}?",
                default=plugin_meta['enabled_by_default']
            )
        except EOFError:
            console.print(f"  Using default: {'Yes' if plugin_meta['enabled_by_default'] else 'No'}")
            enable = plugin_meta['enabled_by_default']

        if enable:
            plugin_config = {
                'enabled': True,
                'access_level': plugin_meta['access_level'],
                'trigger': {
                    'type': plugin_meta['trigger_type']
                }
            }

            for config_key, config_spec in plugin_meta['config'].items():
                # Show help text if available
                if 'help' in config_spec:
                    console.print(f"  [dim]{config_spec['help']}[/dim]")

                # Read existing value from plugins.yml if it exists
                existing_value = read_plugin_config_value(plugin_id, config_key)

                # Use the masked prompt function
                is_password = config_spec['type'] == 'password'
                value = prompt_with_existing_masked(
                    prompt_text=f"  {config_spec['prompt']}",
                    existing_value=existing_value,
                    placeholders=[],  # No placeholders for plugin config
                    is_password=is_password,
                    default=config_spec.get('default', '')
                )

                # For wake_words, convert comma-separated string to list and store in trigger
                if config_key == 'wake_words':
                    # Split by comma and strip whitespace
                    wake_words_list = [w.strip() for w in value.split(',') if w.strip()]
                    plugin_config['trigger']['wake_words'] = wake_words_list
                    # Don't store at root level - only in trigger section
                else:
                    plugin_config[config_key] = value

            selected_plugins[plugin_id] = plugin_config
            console.print(f"  [green]✅ {plugin_meta['name']} configured[/green]\n")

    return selected_plugins

def save_plugin_config(plugins_config):
    """Save plugin configuration to config/plugins.yml"""
    if not plugins_config:
        console.print("[dim]No plugins configured, skipping plugins.yml creation[/dim]")
        return

    config_dir = Path('config')
    config_dir.mkdir(parents=True, exist_ok=True)

    plugins_yml_path = config_dir / 'plugins.yml'

    # Build YAML structure
    yaml_data = {
        'plugins': {}
    }

    for plugin_id, plugin_config in plugins_config.items():
        # Plugin config already includes 'enabled', 'access_level', and 'trigger'
        yaml_data['plugins'][plugin_id] = plugin_config

    # Write to file
    with open(plugins_yml_path, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]✅ Plugin configuration saved to {plugins_yml_path}[/green]")

def setup_tailscale_if_needed(selected_plugins):
    """Check if any selected plugins require Tailscale and prompt for auth key.

    Args:
        selected_plugins: List of plugin IDs selected by user

    Returns:
        Tailscale auth key string if provided, None otherwise
    """
    # Check if any selected plugins require Tailscale
    needs_tailscale = any(
        PLUGINS[p].get('requires_tailscale', False)
        for p in selected_plugins
    )

    if not needs_tailscale:
        return None

    console.print("\n🌐 [bold cyan]Tailscale Configuration[/bold cyan]")
    console.print("Home Assistant plugin requires Tailscale for remote access.")
    console.print("\n[blue][INFO][/blue] The Tailscale Docker container enables Chronicle to access")
    console.print("           services on your Tailscale network (like Home Assistant).")
    console.print()
    console.print("Get your auth key from: [link]https://login.tailscale.com/admin/settings/keys[/link]")
    console.print()

    # Check for existing TS_AUTHKEY in backend .env
    backend_env_path = 'backends/advanced/.env'
    existing_key = read_env_value(backend_env_path, 'TS_AUTHKEY')

    # Use the masked prompt helper
    ts_authkey = prompt_with_existing_masked(
        prompt_text="Tailscale auth key (or press Enter to skip)",
        existing_value=existing_key,
        placeholders=['your-tailscale-auth-key-here'],
        is_password=True,
        default=""
    )

    if not ts_authkey or ts_authkey.strip() == "":
        console.print("[yellow]⚠️  Skipping Tailscale - HA plugin will only work for local instances[/yellow]")
        console.print("[yellow]    You can configure this later in backends/advanced/.env[/yellow]")
        return None

    console.print("[green]✅[/green] Tailscale auth key configured")
    console.print("[blue][INFO][/blue] Start Tailscale with: docker compose --profile tailscale up -d")
    return ts_authkey

def setup_git_hooks():
    """Setup pre-commit hooks for development"""
    console.print("\n🔧 [bold]Setting up development environment...[/bold]")

    try:
        # Install pre-commit if not already installed
        subprocess.run(['pip', 'install', 'pre-commit'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      check=False)

        # Install git hooks
        result = subprocess.run(['pre-commit', 'install', '--hook-type', 'pre-push'],
                              capture_output=True,
                              text=True)

        if result.returncode == 0:
            console.print("✅ [green]Git hooks installed (tests will run before push)[/green]")
        else:
            console.print("⚠️  [yellow]Could not install git hooks (optional)[/yellow]")

        # Also install pre-commit hook
        subprocess.run(['pre-commit', 'install', '--hook-type', 'pre-commit'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      check=False)

    except Exception as e:
        console.print(f"⚠️  [yellow]Could not setup git hooks: {e} (optional)[/yellow]")

def setup_hf_token_if_needed(selected_services):
    """Prompt for Hugging Face token if needed by selected services.

    Args:
        selected_services: List of service names selected by user

    Returns:
        HF_TOKEN string if provided, None otherwise
    """
    # Check if any selected services need HF_TOKEN
    needs_hf_token = 'speaker-recognition' in selected_services or 'advanced' in selected_services

    if not needs_hf_token:
        return None

    console.print("\n🤗 [bold cyan]Hugging Face Token Configuration[/bold cyan]")
    console.print("Required for speaker recognition (PyAnnote models)")
    console.print("\n[blue][INFO][/blue] Get yours from: https://huggingface.co/settings/tokens\n")

    # Check for existing token from speaker-recognition service
    speaker_env_path = 'extras/speaker-recognition/.env'
    existing_token = read_env_value(speaker_env_path, 'HF_TOKEN')

    # Use the masked prompt function
    hf_token = prompt_with_existing_masked(
        prompt_text="Hugging Face Token",
        existing_value=existing_token,
        placeholders=['your_huggingface_token_here', 'your-huggingface-token-here', 'hf_xxxxx'],
        is_password=True,
        default=""
    )

    if hf_token:
        masked = mask_value(hf_token)
        console.print(f"[green]✅ HF_TOKEN configured: {masked}[/green]\n")
        return hf_token
    else:
        console.print("[yellow]⚠️  No HF_TOKEN provided - speaker recognition may fail[/yellow]\n")
        return None

def setup_config_file():
    """Setup config/config.yml from template if it doesn't exist"""
    config_file = Path("config/config.yml")
    config_template = Path("config/config.yml.template")

    if not config_file.exists():
        if config_template.exists():
            # Ensure config/ directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(config_template, config_file)
            console.print("✅ [green]Created config/config.yml from template[/green]")
        else:
            console.print("⚠️  [yellow]config/config.yml.template not found, skipping config setup[/yellow]")
    else:
        console.print("ℹ️  [blue]config/config.yml already exists, keeping existing configuration[/blue]")

def select_transcription_provider():
    """Ask user which transcription provider they want"""
    console.print("\n🎤 [bold cyan]Transcription Provider[/bold cyan]")
    console.print("Choose your speech-to-text provider:")
    console.print()

    choices = {
        "1": "Deepgram (cloud-based, high quality, requires API key)",
        "2": "Parakeet ASR (offline, runs locally, requires GPU)",
        "3": "None (skip transcription setup)"
    }

    for key, desc in choices.items():
        console.print(f"  {key}) {desc}")
    console.print()

    while True:
        try:
            choice = Prompt.ask("Enter choice", default="1")
            if choice in choices:
                if choice == "1":
                    return "deepgram"
                elif choice == "2":
                    return "parakeet"
                elif choice == "3":
                    return "none"
            console.print(f"[red]Invalid choice. Please select from {list(choices.keys())}[/red]")
        except EOFError:
            console.print("Using default: Deepgram")
            return "deepgram"

def main():
    """Main orchestration logic"""
    console.print("🎉 [bold green]Welcome to Chronicle![/bold green]\n")

    # Setup config file from template
    setup_config_file()

    # Setup git hooks first
    setup_git_hooks()

    # Show what's available
    show_service_status()

    # Ask about transcription provider FIRST (determines which services are needed)
    transcription_provider = select_transcription_provider()

    # Service Selection
    selected_services = select_services()

    # Auto-add asr-services if Parakeet was chosen
    if transcription_provider == "parakeet" and 'asr-services' not in selected_services:
        console.print("[blue][INFO][/blue] Auto-adding ASR services for Parakeet transcription")
        selected_services.append('asr-services')

    if not selected_services:
        console.print("\n[yellow]No services selected. Exiting.[/yellow]")
        return

    # Plugin Configuration
    selected_plugins = select_plugins()
    if selected_plugins:
        save_plugin_config(selected_plugins)

    # Tailscale Configuration (if plugins require it)
    ts_authkey = None
    if selected_plugins:
        ts_authkey = setup_tailscale_if_needed(selected_plugins)

    # HF Token Configuration (if services require it)
    hf_token = setup_hf_token_if_needed(selected_services)

    # HTTPS Configuration (for services that need it)
    https_enabled = False
    server_ip = None
    
    # Check if we have services that benefit from HTTPS
    https_services = {'advanced', 'speaker-recognition'} # advanced will always need https then
    needs_https = bool(https_services.intersection(selected_services))
    
    if needs_https:
        console.print("\n🔒 [bold cyan]HTTPS Configuration[/bold cyan]")
        console.print("HTTPS enables microphone access in browsers and secure connections")

        try:
            https_enabled = Confirm.ask("Enable HTTPS for selected services?", default=False)
        except EOFError:
            console.print("Using default: No")
            https_enabled = False

        if https_enabled:
            console.print("\n[blue][INFO][/blue] For distributed deployments, use your Tailscale IP")
            console.print("[blue][INFO][/blue] For local-only access, use 'localhost'")
            console.print("Examples: localhost, 100.64.1.2, your-domain.com")

            # Check for existing SERVER_IP from backend .env
            backend_env_path = 'backends/advanced/.env'
            existing_ip = read_env_value(backend_env_path, 'SERVER_IP')

            # Use the new masked prompt function
            server_ip = prompt_with_existing_masked(
                prompt_text="Server IP/Domain for SSL certificates",
                existing_value=existing_ip,
                placeholders=['localhost', 'your-server-ip-here'],
                is_password=False,
                default="localhost"
            )

            console.print(f"[green]✅[/green] HTTPS configured for: {server_ip}")

    # Obsidian/Neo4j Integration
    obsidian_enabled = False
    neo4j_password = None

    # Check if advanced backend is selected
    if 'advanced' in selected_services:
        console.print("\n🗂️ [bold cyan]Obsidian/Neo4j Integration[/bold cyan]")
        console.print("Enable graph-based knowledge management for Obsidian vault notes")
        console.print()

        try:
            obsidian_enabled = Confirm.ask("Enable Obsidian/Neo4j integration?", default=False)
        except EOFError:
            console.print("Using default: No")
            obsidian_enabled = False

        if obsidian_enabled:
            console.print("[blue][INFO][/blue] Neo4j will be configured for graph-based memory storage")
            console.print()

            # Prompt for Neo4j password
            while True:
                try:
                    neo4j_password = console.input("Neo4j password (min 8 chars) [default: neo4jpassword]: ").strip()
                    if not neo4j_password:
                        neo4j_password = "neo4jpassword"
                    if len(neo4j_password) >= 8:
                        break
                    console.print("[yellow][WARNING][/yellow] Password must be at least 8 characters")
                except EOFError:
                    neo4j_password = "neo4jpassword"
                    console.print(f"Using default password")
                    break

            console.print("[green]✅[/green] Obsidian/Neo4j integration will be configured")

    # Pure Delegation - Run Each Service Setup
    console.print(f"\n📋 [bold]Setting up {len(selected_services)} services...[/bold]")
    
    # Clean up .env files from unselected services (creates backups)
    cleanup_unselected_services(selected_services)
    
    success_count = 0
    failed_services = []

    for service in selected_services:
        if run_service_setup(service, selected_services, https_enabled, server_ip,
                            obsidian_enabled, neo4j_password, ts_authkey, hf_token, transcription_provider):
            success_count += 1
        else:
            failed_services.append(service)

    # Check for Obsidian/Neo4j configuration (read from config.yml)
    obsidian_enabled = False
    if 'advanced' in selected_services and 'advanced' not in failed_services:
        config_yml_path = Path('config/config.yml')
        if config_yml_path.exists():
            try:
                with open(config_yml_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    obsidian_config = config_data.get('memory', {}).get('obsidian', {})
                    obsidian_enabled = obsidian_config.get('enabled', False)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not read config.yml: {e}[/yellow]")

    # Final Summary
    console.print(f"\n🎊 [bold green]Setup Complete![/bold green]")
    console.print(f"✅ {success_count}/{len(selected_services)} services configured successfully")

    if failed_services:
        console.print(f"❌ Failed services: {', '.join(failed_services)}")

    # Inform about Obsidian/Neo4j if configured
    if obsidian_enabled:
        console.print(f"\n📚 [bold cyan]Obsidian Integration Detected[/bold cyan]")
        console.print("   Neo4j will be automatically started with the 'obsidian' profile")
        console.print("   when you start the backend service.")
    
    # Next Steps
    console.print("\n📖 [bold]Next Steps:[/bold]")

    # Configuration info
    console.print("")
    console.print("📝 [bold cyan]Configuration Files Updated:[/bold cyan]")
    console.print("   • [green].env files[/green] - API keys and service URLs")
    console.print("   • [green]config.yml[/green] - Model definitions and memory provider settings")
    console.print("")

    # Development Environment Setup
    console.print("1. Setup development environment (git hooks, testing):")
    console.print("   [cyan]make setup-dev[/cyan]")
    console.print("   [dim]This installs pre-commit hooks to run tests before pushing[/dim]")
    console.print("")

    # Service Management Commands
    console.print("2. Start all configured services:")
    console.print("   [cyan]uv run --with-requirements setup-requirements.txt python services.py start --all --build[/cyan]")
    console.print("")
    console.print("3. Or start individual services:")
    
    configured_services = []
    if 'advanced' in selected_services and 'advanced' not in failed_services:
        configured_services.append("backend")
    if 'speaker-recognition' in selected_services and 'speaker-recognition' not in failed_services:
        configured_services.append("speaker-recognition") 
    if 'asr-services' in selected_services and 'asr-services' not in failed_services:
        configured_services.append("asr-services")
    if 'openmemory-mcp' in selected_services and 'openmemory-mcp' not in failed_services:
        configured_services.append("openmemory-mcp")
        
    if configured_services:
        service_list = " ".join(configured_services)
        console.print(f"   [cyan]uv run --with-requirements setup-requirements.txt python services.py start {service_list}[/cyan]")
    
    console.print("")
    console.print("3. Check service status:")
    console.print("   [cyan]uv run --with-requirements setup-requirements.txt python services.py status[/cyan]")
    
    console.print("")
    console.print("4. Stop services when done:")
    console.print("   [cyan]uv run --with-requirements setup-requirements.txt python services.py stop --all[/cyan]")
    
    console.print(f"\n🚀 [bold]Enjoy Chronicle![/bold]")
    
    # Show individual service usage
    console.print(f"\n💡 [dim]Tip: You can also setup services individually:[/dim]")
    console.print(f"[dim]   cd backends/advanced && uv run --with-requirements ../../setup-requirements.txt python init.py[/dim]")
    console.print(f"[dim]   cd extras/speaker-recognition && uv run --with-requirements ../../setup-requirements.txt python init.py[/dim]")
    console.print(f"[dim]   cd extras/asr-services && uv run --with-requirements ../../setup-requirements.txt python init.py[/dim]")

if __name__ == "__main__":
    main()