#!/usr/bin/env python3
"""
Email Summarizer Plugin Setup Wizard

Configures SMTP credentials and plugin settings.
Follows Chronicle's clean configuration architecture:
- Secrets → backends/advanced/.env
- Non-secret settings → plugins/email_summarizer/config.yml
- Orchestration → config/plugins.yml
"""

import sys
from pathlib import Path

from dotenv import set_key
from rich.console import Console

# Add repo root to path for setup_utils import
project_root = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(project_root))

from setup_utils import (
    prompt_with_existing_masked,
    prompt_value
)

console = Console()


def main():
    """Interactive setup for Email Summarizer plugin"""
    console.print("\n📧 [bold cyan]Email Summarizer Plugin Setup[/bold cyan]")
    console.print("This plugin sends email summaries when conversations complete.\n")

    # Path to main backend .env file
    env_path = str(project_root / "backends" / "advanced" / ".env")

    # SMTP Configuration
    console.print("[bold]SMTP Configuration[/bold]")
    console.print("[dim]For Gmail: Use App Password (Settings > Security > 2FA > App Passwords)[/dim]\n")

    smtp_host = prompt_with_existing_masked(
        prompt_text="SMTP Host",
        env_file_path=env_path,
        env_key="SMTP_HOST",
        placeholders=['your-smtp-host-here'],
        is_password=False,
        default="smtp.gmail.com"
    )

    smtp_port = prompt_value("SMTP Port", default="587")

    smtp_username = prompt_with_existing_masked(
        prompt_text="SMTP Username (your email)",
        env_file_path=env_path,
        env_key="SMTP_USERNAME",
        placeholders=['your-email@example.com'],
        is_password=False
    )

    smtp_password = prompt_with_existing_masked(
        prompt_text="SMTP Password (App Password)",
        env_file_path=env_path,
        env_key="SMTP_PASSWORD",
        placeholders=['your-password-here', 'your-app-password-here'],
        is_password=True  # Shows masked existing value
    )

    # Remove spaces from app password (Google adds spaces when copying)
    smtp_password = smtp_password.replace(" ", "")

    smtp_use_tls = prompt_value("Use TLS? (true/false)", default="true")

    # Email sender configuration
    from_email = prompt_with_existing_masked(
        prompt_text="From Email",
        env_file_path=env_path,
        env_key="FROM_EMAIL",
        placeholders=['noreply@example.com'],
        is_password=False,
        default=smtp_username  # Default to SMTP username
    )

    from_name = prompt_value("From Name", default="Chronicle AI")

    # Save secrets to .env
    console.print("\n💾 [bold]Saving credentials to .env...[/bold]")

    set_key(env_path, "SMTP_HOST", smtp_host)
    set_key(env_path, "SMTP_PORT", smtp_port)
    set_key(env_path, "SMTP_USERNAME", smtp_username)
    set_key(env_path, "SMTP_PASSWORD", smtp_password)
    set_key(env_path, "SMTP_USE_TLS", smtp_use_tls)
    set_key(env_path, "FROM_EMAIL", from_email)
    set_key(env_path, "FROM_NAME", from_name)

    console.print("[green]✅ SMTP credentials saved to backends/advanced/.env[/green]")

    # Inform user about next steps
    console.print("\n[bold cyan]✅ Email Summarizer plugin configured successfully![/bold cyan]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Enable the plugin in [cyan]config/plugins.yml[/cyan]:")
    console.print("   [dim]plugins:[/dim]")
    console.print("   [dim]  email_summarizer:[/dim]")
    console.print("   [dim]    enabled: true[/dim]")
    console.print()
    console.print("2. Adjust plugin settings in [cyan]plugins/email_summarizer/config.yml[/cyan]")
    console.print("   (subject prefix, summary length, etc.)")
    console.print()
    console.print("3. Restart the backend to apply changes:")
    console.print("   [dim]cd backends/advanced && docker compose restart[/dim]")
    console.print()
    console.print("[dim]Plugin configuration architecture:[/dim]")
    console.print("[dim]  • Secrets:      backends/advanced/.env[/dim]")
    console.print("[dim]  • Settings:     plugins/email_summarizer/config.yml[/dim]")
    console.print("[dim]  • Orchestration: config/plugins.yml[/dim]")
    console.print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error during setup: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
