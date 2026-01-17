#!/usr/bin/env python3
"""
Email Summarizer Plugin Setup Wizard
Configures SMTP credentials and plugin settings
"""

import sys
from pathlib import Path
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm
import getpass

console = Console()

def main():
    console.print("\n📧 [bold cyan]Email Summarizer Plugin Setup[/bold cyan]")
    console.print("This plugin sends email summaries when conversations complete.\n")

    # Prompt for SMTP configuration
    console.print("[bold]SMTP Configuration[/bold]")
    console.print("[dim]For Gmail: Use App Password (Settings > Security > 2FA > App Passwords)[/dim]\n")

    smtp_host = Prompt.ask("SMTP Host", default="smtp.gmail.com")
    smtp_port = Prompt.ask("SMTP Port", default="587")
    smtp_username = Prompt.ask("SMTP Username (your email)")
    smtp_password = getpass.getpass("SMTP Password (App Password): ")
    # Remove spaces from app password (Google adds spaces when copying)
    smtp_password = smtp_password.replace(" ", "")
    smtp_use_tls = Confirm.ask("Use TLS?", default=True)

    from_email = Prompt.ask("From Email", default=smtp_username)
    from_name = Prompt.ask("From Name", default="Chronicle AI")

    # Email content options
    console.print("\n[bold]Email Content Options[/bold]")
    subject_prefix = Prompt.ask("Email Subject Prefix", default="Conversation Summary")
    summary_sentences = Prompt.ask("Summary max sentences", default="3")

    # Build plugin config
    plugin_config = {
        'enabled': True,
        'events': ['conversation.complete'],
        'condition': {
            'type': 'always'
        },
        'smtp_host': smtp_host,
        'smtp_port': int(smtp_port),
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'smtp_use_tls': smtp_use_tls,
        'from_email': from_email,
        'from_name': from_name,
        'subject_prefix': subject_prefix,
        'summary_max_sentences': int(summary_sentences),
        'include_conversation_id': True,
        'include_duration': True
    }

    # Find project root (7 levels up from this file)
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
    config_dir = project_root / 'config'
    plugins_yml = config_dir / 'plugins.yml'

    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    # Load existing plugins.yml or create new
    if plugins_yml.exists():
        with open(plugins_yml, 'r') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    if 'plugins' not in config:
        config['plugins'] = {}

    # Add/update email_summarizer config
    config['plugins']['email_summarizer'] = plugin_config

    # Write back to plugins.yml
    with open(plugins_yml, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"\n[green]✅ Email Summarizer configured successfully[/green]")
    console.print(f"[green]✅ Configuration written to {plugins_yml}[/green]")

    # Note about environment variables
    console.print(f"\n[yellow]Note: SMTP credentials are stored in plugins.yml[/yellow]")
    console.print(f"[dim]You can also use environment variables in backends/advanced/.env:[/dim]")
    console.print(f"[dim]  SMTP_HOST={smtp_host}[/dim]")
    console.print(f"[dim]  SMTP_PORT={smtp_port}[/dim]")
    console.print(f"[dim]  SMTP_USERNAME={smtp_username}[/dim]")
    console.print(f"[dim]  SMTP_PASSWORD=<your-app-password>[/dim]")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error during setup: {e}[/red]")
        sys.exit(1)
