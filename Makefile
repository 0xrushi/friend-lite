# ========================================
# Friend-Lite Management System
# ========================================
# Central management interface for Friend-Lite project
# Handles configuration, deployment, and maintenance tasks

# Load environment variables from .env file (if it exists)
ifneq (,$(wildcard ./.env))
    include .env
    export $(shell sed 's/=.*//' .env | grep -v '^\s*$$' | grep -v '^\s*\#')
endif

# Load configuration definitions for Kubernetes
# Use config-k8s.env for K8s deployments
ifneq (,$(wildcard ./config-k8s.env))
    include config-k8s.env
    export $(shell sed 's/=.*//' config-k8s.env | grep -v '^\s*$$' | grep -v '^\s*\#')
else
    # Fallback to config.env for backwards compatibility
    ifneq (,$(wildcard ./config.env))
        include config.env
        export $(shell sed 's/=.*//' config.env | grep -v '^\s*$$' | grep -v '^\s*\#')
    endif
endif

# Load secrets (gitignored) - required for K8s secrets generation
ifneq (,$(wildcard ./.env.secrets))
    include .env.secrets
    export $(shell sed 's/=.*//' .env.secrets | grep -v '^\s*$$' | grep -v '^\s*\#')
endif

# Script directories
SCRIPTS_DIR := scripts
K8S_SCRIPTS_DIR := $(SCRIPTS_DIR)/k8s

.PHONY: help menu wizard setup-secrets setup-tailscale setup-environment check-secrets setup-k8s setup-infrastructure setup-rbac setup-storage-pvc config config-docker config-k8s config-all clean deploy deploy-docker deploy-k8s deploy-k8s-full deploy-infrastructure deploy-apps check-infrastructure check-apps build-backend up-backend down-backend k8s-status k8s-cleanup k8s-purge audio-manage mycelia-sync-status mycelia-sync-all mycelia-sync-user mycelia-check-orphans mycelia-reassign-orphans test-robot test-robot-integration test-robot-unit test-robot-endpoints test-robot-specific test-robot-clean

# Default target
.DEFAULT_GOAL := menu

menu: ## Show interactive menu (default)
	@echo "🎯 Friend-Lite Management System"
	@echo "================================"
	@echo
	@echo "🧙 Setup:"
	@echo "  wizard             🧙 Interactive setup wizard (secrets + Tailscale + environment)"
	@echo "  setup-secrets      🔐 Configure API keys and passwords"
	@echo "  setup-tailscale    🌐 Configure Tailscale for distributed deployment"
	@echo "  setup-environment  📦 Create a custom environment"
	@echo
	@echo "📋 Quick Actions:"
	@echo "  setup-dev          🛠️  Setup development environment (git hooks, pre-commit)"
	@echo "  setup-k8s          🏗️  Complete Kubernetes setup (registry + infrastructure + RBAC)"
	@echo "  config             📝 Generate all configuration files"
	@echo "  deploy             🚀 Deploy using configured mode ($(DEPLOYMENT_MODE))"
	@echo "  k8s-status         📊 Check Kubernetes cluster status"
	@echo "  k8s-cleanup        🧹 Clean up Kubernetes resources"
	@echo "  audio-manage       🎵 Manage audio files"
	@echo
	@echo "🧪 Testing:"
	@echo "  test-robot         🧪 Run all Robot Framework tests"
	@echo "  test-robot-integration 🔬 Run integration tests only"
	@echo "  test-robot-endpoints 🌐 Run endpoint tests only"
	@echo
	@echo "📝 Configuration:"
	@echo "  config-docker      🐳 Generate Docker Compose .env files"
	@echo "  config-k8s         ☸️  Generate Kubernetes files (Skaffold env + ConfigMap/Secret)"
	@echo
	@echo "🚀 Deployment:"
	@echo "  deploy-docker      🐳 Deploy with Docker Compose"
	@echo "  deploy-k8s         ☸️  Deploy to Kubernetes with Skaffold"
	@echo "  deploy-k8s-full    🏗️  Deploy infrastructure + applications"
	@echo
	@echo "🔧 Utilities:"
	@echo "  k8s-purge          🗑️  Purge unused images (registry + container)"
	@echo "  check-infrastructure 🔍 Check infrastructure services"
	@echo "  check-apps         🔍 Check application services"
	@echo "  clean              🧹 Clean up generated files"
	@echo
	@echo "🔄 Mycelia Sync:"
	@echo "  mycelia-sync-status      📊 Show Mycelia OAuth sync status"
	@echo "  mycelia-sync-all         🔄 Sync all Friend-Lite users to Mycelia"
	@echo "  mycelia-sync-user        👤 Sync specific user (EMAIL=user@example.com)"
	@echo "  mycelia-check-orphans    🔍 Find orphaned Mycelia objects"
	@echo "  mycelia-reassign-orphans ♻️  Reassign orphans (EMAIL=admin@example.com)"
	@echo
	@echo "Current configuration:"
	@echo "  DOMAIN: $(DOMAIN)"
	@echo "  DEPLOYMENT_MODE: $(DEPLOYMENT_MODE)"
	@echo "  CONTAINER_REGISTRY: $(CONTAINER_REGISTRY)"
	@echo "  SPEAKER_NODE: $(SPEAKER_NODE)"
	@echo "  INFRASTRUCTURE_NAMESPACE: $(INFRASTRUCTURE_NAMESPACE)"
	@echo "  APPLICATION_NAMESPACE: $(APPLICATION_NAMESPACE)"
	@echo
	@echo "💡 Tip: Run 'make help' for detailed help on any target"

help: ## Show detailed help for all targets
	@echo "🎯 Friend-Lite Management System - Detailed Help"
	@echo "================================================"
	@echo
	@echo "🏗️  KUBERNETES SETUP:"
	@echo "  setup-k8s          Complete initial Kubernetes setup"
	@echo "                     - Configures insecure registry access"
	@echo "                     - Sets up infrastructure services (MongoDB, Qdrant)"
	@echo "                     - Creates shared models PVC"
	@echo "                     - Sets up cross-namespace RBAC"
	@echo "                     - Generates and applies configuration"
	@echo "  setup-infrastructure Deploy infrastructure services (MongoDB, Qdrant)"
	@echo "  setup-rbac         Set up cross-namespace RBAC"
	@echo "  setup-storage-pvc  Create shared models PVC"
	@echo
	@echo "📝 CONFIGURATION:"
	@echo "  config             Generate all configuration files (Docker + K8s)"
	@echo "  config-docker      Generate Docker Compose .env files"
	@echo "  config-k8s         Generate Kubernetes files (Skaffold env + ConfigMap/Secret)"
	@echo
	@echo "🚀 DEPLOYMENT:"
	@echo "  deploy             Deploy using configured deployment mode"
	@echo "  deploy-docker      Deploy with Docker Compose"
	@echo "  deploy-k8s         Deploy to Kubernetes with Skaffold"
	@echo "  deploy-k8s-full    Deploy infrastructure + applications"
	@echo
	@echo "🔧 KUBERNETES UTILITIES:"
	@echo "  k8s-status         Check Kubernetes cluster status and health"
	@echo "  k8s-cleanup        Clean up Kubernetes resources and storage"
	@echo "  k8s-purge          Purge unused images (registry + container)"
	@echo
	@echo "🎵 AUDIO MANAGEMENT:"
	@echo "  audio-manage       Interactive audio file management"
	@echo
	@echo "🔄 MYCELIA SYNC:"
	@echo "  mycelia-sync-status Show Mycelia OAuth sync status for all users"
	@echo "  mycelia-sync-all   Sync all Friend-Lite users to Mycelia OAuth"
	@echo "  mycelia-sync-user  Sync specific user (EMAIL=user@example.com)"
	@echo "  mycelia-check-orphans Find Mycelia objects without Friend-Lite owner"
	@echo "  mycelia-reassign-orphans Reassign orphaned objects (EMAIL=admin@example.com)"
	@echo
	@echo "🧪 ROBOT FRAMEWORK TESTING:"
	@echo "  test-robot         Run all Robot Framework tests"
	@echo "  test-robot-integration Run integration tests only"
	@echo "  test-robot-endpoints Run endpoint tests only"
	@echo "  test-robot-specific FILE=path Run specific test file"
	@echo "  test-robot-clean   Clean up test results"
	@echo
	@echo "🔍 MONITORING:"
	@echo "  check-infrastructure Check if infrastructure services are running"
	@echo "  check-apps         Check if application services are running"
	@echo
	@echo "🧹 CLEANUP:"
	@echo "  clean              Clean up generated configuration files"

# ========================================
# DEVELOPMENT SETUP
# ========================================

setup-dev: ## Setup development environment (git hooks, pre-commit)
	@echo "🛠️  Setting up development environment..."
	@echo ""
	@echo "📦 Installing pre-commit..."
	@pip install pre-commit 2>/dev/null || pip3 install pre-commit
	@echo ""
	@echo "🔧 Installing git hooks..."
	@pre-commit install --hook-type pre-push
	@pre-commit install --hook-type pre-commit
	@echo ""
	@echo "✅ Development environment setup complete!"
	@echo ""
	@echo "💡 Hooks installed:"
	@echo "  • Robot Framework tests run before push"
	@echo "  • Black/isort format Python code on commit"
	@echo "  • Code quality checks on commit"
	@echo ""
	@echo "⚙️  To skip hooks: git push --no-verify / git commit --no-verify"

# ========================================
# INTERACTIVE SETUP WIZARD
# ========================================

.PHONY: wizard setup-secrets setup-tailscale setup-environment check-secrets

wizard: ## 🧙 Interactive setup wizard - guides through complete Friend-Lite setup
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧙 Friend-Lite Setup Wizard"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "This wizard will guide you through:"
	@echo "  1. 🔐 Setting up secrets (API keys, passwords)"
	@echo "  2. 🌐 Optionally configuring Tailscale for distributed deployment"
	@echo "  3. 📦 Creating a custom environment"
	@echo "  4. 🚀 Starting your Friend-Lite instance"
	@echo ""
	@read -p "Press Enter to continue or Ctrl+C to exit..."
	@echo ""
	@$(MAKE) --no-print-directory setup-secrets
	@echo ""
	@$(MAKE) --no-print-directory setup-tailscale
	@echo ""
	@$(MAKE) --no-print-directory setup-environment
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Setup Complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 Next Steps:"
	@echo ""
	@if [ -f ".env.secrets" ] && [ -d "environments" ]; then \
		echo "  Start your environment:"; \
		echo "    ./start-env.sh $${ENV_NAME:-dev}"; \
		echo ""; \
		echo "  Or with optional services:"; \
		echo "    ./start-env.sh $${ENV_NAME:-dev} --profile mycelia"; \
		echo "    ./start-env.sh $${ENV_NAME:-dev} --profile speaker"; \
	else \
		echo "  ⚠️  Some setup steps were skipped. Run individual targets:"; \
		echo "    make setup-secrets"; \
		echo "    make setup-environment"; \
	fi
	@echo ""
	@echo "📚 Documentation:"
	@echo "  • ENVIRONMENTS.md - Environment system overview"
	@echo "  • SSL_SETUP.md - Tailscale and SSL configuration"
	@echo "  • SETUP.md - Detailed setup instructions"
	@echo ""

check-secrets: ## Check if secrets file exists and is configured
	@if [ ! -f ".env.secrets" ]; then \
		echo "❌ .env.secrets not found"; \
		exit 1; \
	fi
	@if ! grep -q "^AUTH_SECRET_KEY=" .env.secrets || grep -q "your-super-secret" .env.secrets; then \
		echo "❌ .env.secrets exists but needs configuration"; \
		exit 1; \
	fi
	@echo "✅ Secrets file configured"

setup-secrets: ## 🔐 Interactive secrets setup (API keys, passwords)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔐 Step 1: Secrets Configuration"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@if [ -f ".env.secrets" ]; then \
		echo "ℹ️  .env.secrets already exists"; \
		echo ""; \
		read -p "Do you want to reconfigure it? (y/N): " reconfigure; \
		if [ "$$reconfigure" != "y" ] && [ "$$reconfigure" != "Y" ]; then \
			echo ""; \
			echo "✅ Keeping existing secrets"; \
			exit 0; \
		fi; \
		echo ""; \
		echo "📝 Backing up existing .env.secrets..."; \
		cp .env.secrets .env.secrets.backup.$$(date +%Y%m%d_%H%M%S); \
		echo ""; \
	else \
		echo "📝 Creating .env.secrets from template..."; \
		cp .env.secrets.template .env.secrets; \
		echo "✅ Created .env.secrets"; \
		echo ""; \
	fi
	@echo "🔑 Required Secrets Configuration"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Let's configure your secrets. Press Enter to skip optional ones."
	@echo ""
	@# JWT Secret Key (required)
	@echo "1️⃣  JWT Secret Key (required for authentication)"
	@echo "   This is used to sign JWT tokens. Should be random and secure."
	@read -p "   Enter JWT secret key (or press Enter to generate): " jwt_key; \
	if [ -z "$$jwt_key" ]; then \
		jwt_key=$$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1); \
		echo "   ✅ Generated random key: $$jwt_key"; \
	fi; \
	sed -i.bak "s|^AUTH_SECRET_KEY=.*|AUTH_SECRET_KEY=$$jwt_key|" .env.secrets && rm .env.secrets.bak
	@echo ""
	@# Admin credentials
	@echo "2️⃣  Admin Account"
	@read -p "   Admin email (default: admin@example.com): " admin_email; \
	admin_email=$${admin_email:-admin@example.com}; \
	sed -i.bak "s|^ADMIN_EMAIL=.*|ADMIN_EMAIL=$$admin_email|" .env.secrets && rm .env.secrets.bak; \
	read -sp "   Admin password: " admin_pass; echo ""; \
	if [ -n "$$admin_pass" ]; then \
		sed -i.bak "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$$admin_pass|" .env.secrets && rm .env.secrets.bak; \
	fi
	@echo ""
	@# OpenAI API Key
	@echo "3️⃣  OpenAI API Key (required for memory extraction)"
	@echo "   Get your key from: https://platform.openai.com/api-keys"
	@read -p "   OpenAI API key (or press Enter to skip): " openai_key; \
	if [ -n "$$openai_key" ]; then \
		sed -i.bak "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$$openai_key|" .env.secrets && rm .env.secrets.bak; \
	fi
	@echo ""
	@# Deepgram API Key
	@echo "4️⃣  Deepgram API Key (recommended for transcription)"
	@echo "   Get your key from: https://console.deepgram.com/"
	@read -p "   Deepgram API key (or press Enter to skip): " deepgram_key; \
	if [ -n "$$deepgram_key" ]; then \
		sed -i.bak "s|^DEEPGRAM_API_KEY=.*|DEEPGRAM_API_KEY=$$deepgram_key|" .env.secrets && rm .env.secrets.bak; \
	fi
	@echo ""
	@# Optional: Mistral API Key
	@echo "5️⃣  Mistral API Key (optional - alternative transcription)"
	@echo "   Get your key from: https://console.mistral.ai/"
	@read -p "   Mistral API key (or press Enter to skip): " mistral_key; \
	if [ -n "$$mistral_key" ]; then \
		sed -i.bak "s|^MISTRAL_API_KEY=.*|MISTRAL_API_KEY=$$mistral_key|" .env.secrets && rm .env.secrets.bak; \
	fi
	@echo ""
	@# Optional: Hugging Face Token
	@echo "6️⃣  Hugging Face Token (optional - for speaker recognition models)"
	@echo "   Get your token from: https://huggingface.co/settings/tokens"
	@read -p "   HF token (or press Enter to skip): " hf_token; \
	if [ -n "$$hf_token" ]; then \
		sed -i.bak "s|^HF_TOKEN=.*|HF_TOKEN=$$hf_token|" .env.secrets && rm .env.secrets.bak; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Secrets configured successfully!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📄 Configuration saved to: .env.secrets"
	@echo "🔒 This file is gitignored and will not be committed"
	@echo ""

setup-tailscale: ## 🌐 Interactive Tailscale setup for distributed deployment
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 Step 2: Tailscale Configuration (Optional)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Tailscale enables secure distributed deployments:"
	@echo "  • Run services on different machines"
	@echo "  • Secure service-to-service communication"
	@echo "  • Access from mobile devices"
	@echo "  • Automatic HTTPS with 'tailscale serve'"
	@echo ""
	@read -p "Do you want to configure Tailscale? (y/N): " use_tailscale; \
	if [ "$$use_tailscale" != "y" ] && [ "$$use_tailscale" != "Y" ]; then \
		echo ""; \
		echo "ℹ️  Skipping Tailscale setup"; \
		echo "   You can run this later with: make setup-tailscale"; \
		exit 0; \
	fi
	@echo ""
	@# Check if Tailscale is installed
	@if ! command -v tailscale >/dev/null 2>&1; then \
		echo "❌ Tailscale not found"; \
		echo ""; \
		echo "📦 Install Tailscale:"; \
		echo "   curl -fsSL https://tailscale.com/install.sh | sh"; \
		echo "   sudo tailscale up"; \
		echo ""; \
		echo "Then run this setup again: make setup-tailscale"; \
		exit 1; \
	fi
	@echo "✅ Tailscale is installed"
	@echo ""
	@# Get Tailscale status
	@echo "📊 Checking Tailscale status..."
	@if ! tailscale status >/dev/null 2>&1; then \
		echo "❌ Tailscale is not running"; \
		echo ""; \
		echo "🔧 Start Tailscale:"; \
		echo "   sudo tailscale up"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Tailscale is running"
	@echo ""
	@echo "📋 Your Tailscale devices:"
	@echo ""
	@tailscale status | head -n 10
	@echo ""
	@# Get Tailscale hostname
	@echo "🏷️  Tailscale Hostname Configuration"
	@echo ""
	@echo "Your Tailscale hostname is the DNS name assigned to THIS machine."
	@echo "It's different from the IP address - it's a permanent name."
	@echo ""
	@echo "📋 To find your Tailscale hostname:"
	@echo "   1. Run: tailscale status"
	@echo "   2. Look for this machine's name in the first column"
	@echo "   3. The full hostname is shown on the right (ends in .ts.net)"
	@echo ""
	@echo "Example output:"
	@echo "   anubis    100.x.x.x   anubis.tail12345.ts.net   <-- Your hostname"
	@echo ""
	@default_hostname=$$(tailscale status --json 2>/dev/null | grep -o '"DNSName":"[^"]*"' | head -1 | cut -d'"' -f4 | sed 's/\.$$//'); \
	if [ -n "$$default_hostname" ]; then \
		echo "💡 Auto-detected hostname for THIS machine: $$default_hostname"; \
		echo ""; \
	fi; \
	read -p "Tailscale hostname [$$default_hostname]: " tailscale_hostname; \
	tailscale_hostname=$${tailscale_hostname:-$$default_hostname}; \
	if [ -z "$$tailscale_hostname" ]; then \
		echo ""; \
		echo "❌ No hostname provided"; \
		exit 1; \
	fi; \
	export TAILSCALE_HOSTNAME=$$tailscale_hostname; \
	echo ""; \
	echo "✅ Using Tailscale hostname: $$tailscale_hostname"
	@echo ""
	@# SSL Setup
	@echo "🔐 SSL Certificate Configuration"
	@echo ""
	@echo "How do you want to handle HTTPS?"
	@echo "  1) Use 'tailscale serve' (automatic HTTPS, recommended)"
	@echo "  2) Generate self-signed certificates"
	@echo "  3) Skip SSL setup"
	@echo ""
	@read -p "Choose option (1-3) [1]: " ssl_choice; \
	ssl_choice=$${ssl_choice:-1}; \
	case $$ssl_choice in \
		1) \
			echo ""; \
			echo "✅ Will use 'tailscale serve' for automatic HTTPS"; \
			echo ""; \
			echo "📝 After starting services, run:"; \
			echo "   tailscale serve https / http://localhost:8000"; \
			echo "   tailscale serve https / http://localhost:5173"; \
			echo ""; \
			export HTTPS_ENABLED=true; \
			;; \
		2) \
			echo ""; \
			echo "🔐 Generating SSL certificates for $$tailscale_hostname..."; \
			if [ -f "backends/advanced/ssl/generate-ssl.sh" ]; then \
				cd backends/advanced && ./ssl/generate-ssl.sh $$tailscale_hostname && cd ../..; \
				echo ""; \
				echo "✅ SSL certificates generated"; \
			else \
				echo "❌ SSL generation script not found"; \
				exit 1; \
			fi; \
			export HTTPS_ENABLED=true; \
			;; \
		3) \
			echo ""; \
			echo "ℹ️  Skipping SSL setup"; \
			export HTTPS_ENABLED=false; \
			;; \
		*) \
			echo ""; \
			echo "❌ Invalid choice"; \
			exit 1; \
			;; \
	esac
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Tailscale configuration complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""

setup-environment: ## 📦 Create a custom environment configuration
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Step 3: Environment Setup"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Environments allow you to:"
	@echo "  • Run multiple isolated instances (dev, staging, prod)"
	@echo "  • Use different databases and ports for each"
	@echo "  • Test changes without affecting production"
	@echo ""
	@# Check existing environments
	@if [ -d "environments" ] && [ -n "$$(ls -A environments/*.env 2>/dev/null)" ]; then \
		echo "📋 Existing environments:"; \
		ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$$||' | sed 's/^/  - /'; \
		echo ""; \
	fi
	@# Get environment name
	@read -p "Environment name [dev]: " env_name; \
	env_name=$${env_name:-dev}; \
	mkdir -p environments; \
	env_file="environments/$$env_name.env"; \
	echo ""; \
	if [ -f "$$env_file" ]; then \
		echo "⚠️  Environment '$$env_name' already exists"; \
		read -p "Do you want to overwrite it? (y/N): " overwrite; \
		if [ "$$overwrite" != "y" ] && [ "$$overwrite" != "Y" ]; then \
			echo ""; \
			echo "ℹ️  Keeping existing environment"; \
			exit 0; \
		fi; \
		echo ""; \
		cp "$$env_file" "$$env_file.backup.$$(date +%Y%m%d_%H%M%S)"; \
		echo "📝 Backed up existing environment"; \
		echo ""; \
	fi
	@# Get port offset
	@echo "🔢 Port Configuration"; \
	echo ""; \
	echo "Each environment needs a unique port offset to avoid conflicts."; \
	echo "  dev:     0   (8000, 5173, 27017, ...)"; \
	echo "  staging: 100 (8100, 5273, 27117, ...)"; \
	echo "  prod:    200 (8200, 5373, 27217, ...)"; \
	echo ""; \
	read -p "Port offset [0]: " port_offset; \
	port_offset=$${port_offset:-0}; \
	echo ""
	@# Get database names
	@echo "💾 Database Configuration"; \
	echo ""; \
	read -p "MongoDB database name [friend-lite-$$env_name]: " mongodb_db; \
	mongodb_db=$${mongodb_db:-friend-lite-$$env_name}; \
	read -p "Mycelia database name [mycelia-$$env_name]: " mycelia_db; \
	mycelia_db=$${mycelia_db:-mycelia-$$env_name}; \
	echo ""
	@# Optional services
	@echo "🔌 Optional Services"; \
	echo ""; \
	read -p "Enable Mycelia? (y/N): " enable_mycelia; \
	read -p "Enable Speaker Recognition? (y/N): " enable_speaker; \
	read -p "Enable OpenMemory MCP? (y/N): " enable_openmemory; \
	read -p "Enable Parakeet ASR? (y/N): " enable_parakeet; \
	services=""; \
	if [ "$$enable_mycelia" = "y" ] || [ "$$enable_mycelia" = "Y" ]; then \
		services="$$services mycelia"; \
	fi; \
	if [ "$$enable_speaker" = "y" ] || [ "$$enable_speaker" = "Y" ]; then \
		services="$$services speaker"; \
	fi; \
	if [ "$$enable_openmemory" = "y" ] || [ "$$enable_openmemory" = "Y" ]; then \
		services="$$services openmemory"; \
	fi; \
	if [ "$$enable_parakeet" = "y" ] || [ "$$enable_parakeet" = "Y" ]; then \
		services="$$services parakeet"; \
	fi; \
	echo ""
	@# Tailscale settings (from previous step or ask)
	@if [ -n "$$TAILSCALE_HOSTNAME" ]; then \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "🌐 Tailscale Configuration"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo ""; \
		echo "✅ Using Tailscale configuration from previous step:"; \
		echo "   Hostname: $$TAILSCALE_HOSTNAME"; \
		echo "   HTTPS:    $$HTTPS_ENABLED"; \
		echo ""; \
		tailscale_hostname=$$TAILSCALE_HOSTNAME; \
		https_enabled=$$HTTPS_ENABLED; \
	else \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "🌐 Tailscale Configuration (Optional)"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo ""; \
		echo "⚠️  You skipped Tailscale setup earlier."; \
		echo ""; \
		echo "You can still configure it for this environment:"; \
		echo "  • Enter your Tailscale hostname (from 'tailscale status')"; \
		echo "  • Or press Enter to skip (HTTP only, no Tailscale)"; \
		echo ""; \
		read -p "Tailscale hostname (or press Enter to skip): " tailscale_hostname; \
		if [ -n "$$tailscale_hostname" ]; then \
			echo ""; \
			echo "⚠️  Note: SSL certificates were not generated."; \
			echo "   To generate them later, run:"; \
			echo "   cd backends/advanced && ./ssl/generate-ssl.sh $$tailscale_hostname"; \
			echo ""; \
			https_enabled=true; \
		else \
			https_enabled=false; \
		fi; \
	fi; \
	echo ""
	@# Write environment file
	@echo "📝 Creating environment file: $$env_file"; \
	echo ""; \
	printf "# ========================================\n" > "$$env_file"; \
	printf "# Friend-Lite Environment: %s\n" "$$env_name" >> "$$env_file"; \
	printf "# ========================================\n" >> "$$env_file"; \
	printf "# Generated: %s\n" "$$(date)" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	printf "# Environment identification\n" >> "$$env_file"; \
	printf "ENV_NAME=%s\n" "$$env_name" >> "$$env_file"; \
	printf "COMPOSE_PROJECT_NAME=friend-lite-%s\n" "$$env_name" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	printf "# Port offset (each environment needs unique ports)\n" >> "$$env_file"; \
	printf "PORT_OFFSET=%s\n" "$$port_offset" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	printf "# Data directory (isolated per environment)\n" >> "$$env_file"; \
	printf "DATA_DIR=./data/%s\n" "$$env_name" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	printf "# Database names (isolated per environment)\n" >> "$$env_file"; \
	printf "MONGODB_DATABASE=%s\n" "$$mongodb_db" >> "$$env_file"; \
	printf "MYCELIA_DB=%s\n" "$$mycelia_db" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	printf "# Optional services\n" >> "$$env_file"; \
	printf "SERVICES=%s\n" "$$services" >> "$$env_file"; \
	printf "\n" >> "$$env_file"; \
	if [ -n "$$tailscale_hostname" ]; then \
		printf "# Tailscale configuration\n" >> "$$env_file"; \
		printf "TAILSCALE_HOSTNAME=%s\n" "$$tailscale_hostname" >> "$$env_file"; \
		printf "HTTPS_ENABLED=%s\n" "$$https_enabled" >> "$$env_file"; \
		printf "\n" >> "$$env_file"; \
	fi; \
	echo "✅ Environment created: $$env_name"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Environment setup complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📄 Environment file: $$env_file"
	@echo ""
	@echo "🚀 Start this environment with:"
	@echo "   ./start-env.sh $$env_name"
	@echo ""

# ========================================
# KUBERNETES SETUP
# ========================================

setup-k8s: ## Initial Kubernetes setup (registry + infrastructure)
	@echo "🏗️  Starting Kubernetes initial setup..."
	@echo "This will set up the complete infrastructure for Friend-Lite"
	@echo
	@echo "📋 Setup includes:"
	@echo "  • Insecure registry configuration"
	@echo "  • Infrastructure services (MongoDB, Qdrant)"
	@echo "  • Shared models PVC for speaker recognition"
	@echo "  • Cross-namespace RBAC"
	@echo "  • Configuration generation and application"
	@echo
	@read -p "Enter your Kubernetes node IP address: " node_ip; \
	if [ -z "$$node_ip" ]; then \
		echo "❌ Node IP is required"; \
		exit 1; \
	fi; \
	echo "🔧 Step 1: Configuring insecure registry access on $$node_ip..."; \
	$(SCRIPTS_DIR)/configure-insecure-registry-remote.sh $$node_ip; \
	echo "📦 Step 2: Setting up storage for speaker recognition..."; \
	$(K8S_SCRIPTS_DIR)/setup-storage.sh; \
	echo "📝 Step 3: Generating configuration files..."; \
	$(MAKE) config-k8s; \
	echo "🏗️  Step 4: Setting up infrastructure services..."; \
	$(MAKE) setup-infrastructure; \
	echo "🔐 Step 5: Setting up cross-namespace RBAC..."; \
	$(MAKE) setup-rbac; \
	echo "💾 Step 6: Creating shared models PVC..."; \
	$(MAKE) setup-storage-pvc; \
	echo "✅ Kubernetes initial setup completed!"
	@echo
	@echo "🎯 Next steps:"
	@echo "  • Run 'make deploy' to deploy applications"
	@echo "  • Run 'make k8s-status' to check cluster status"
	@echo "  • Run 'make help' for more options"

setup-infrastructure: ## Set up infrastructure services (MongoDB, Qdrant)
	@echo "🏗️  Setting up infrastructure services..."
	@echo "Deploying MongoDB and Qdrant to $(INFRASTRUCTURE_NAMESPACE) namespace..."
	@set -a; source skaffold.env; set +a; skaffold run --profile=infrastructure --default-repo=$(CONTAINER_REGISTRY)
	@echo "⏳ Waiting for infrastructure services to be ready..."
	@kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mongodb -n $(INFRASTRUCTURE_NAMESPACE) --timeout=300s || echo "⚠️  MongoDB not ready yet"
	@kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=qdrant -n $(INFRASTRUCTURE_NAMESPACE) --timeout=300s || echo "⚠️  Qdrant not ready yet"
	@echo "✅ Infrastructure services deployed"

setup-rbac: ## Set up cross-namespace RBAC
	@echo "🔐 Setting up cross-namespace RBAC..."
	@kubectl apply -f k8s-manifests/cross-namespace-rbac.yaml
	@echo "✅ Cross-namespace RBAC configured"

setup-storage-pvc: ## Set up shared models PVC
	@echo "💾 Setting up shared models PVC..."
	@kubectl apply -f k8s-manifests/shared-models-pvc.yaml
	@echo "⏳ Waiting for PVC to be bound..."
	@kubectl wait --for=condition=bound pvc/shared-models-cache -n speech --timeout=60s || echo "⚠️  PVC not bound yet"
	@echo "✅ Shared models PVC created"

# ========================================
# CONFIGURATION
# ========================================

config: config-all ## Generate all configuration files

config-docker: ## Generate Docker Compose configuration files
	@echo "🐳 Generating Docker Compose configuration files..."
	@CONFIG_FILE=config.env.dev python3 scripts/generate-docker-configs.py
	@echo "✅ Docker Compose configuration files generated"

config-k8s: ## Generate Kubernetes configuration files (ConfigMap/Secret only - no .env files)
	@echo "☸️  Generating Kubernetes configuration files..."
	@python3 scripts/generate-k8s-configs.py
	@echo "📦 Applying ConfigMap and Secret to Kubernetes..."
	@kubectl apply -f k8s-manifests/configmap.yaml -n $(APPLICATION_NAMESPACE) 2>/dev/null || echo "⚠️  ConfigMap not applied (cluster not available?)"
	@kubectl apply -f k8s-manifests/secrets.yaml -n $(APPLICATION_NAMESPACE) 2>/dev/null || echo "⚠️  Secret not applied (cluster not available?)"
	@echo "📦 Copying ConfigMap and Secret to speech namespace..."
	@kubectl get configmap friend-lite-config -n $(APPLICATION_NAMESPACE) -o yaml | \
		sed -e '/namespace:/d' -e '/resourceVersion:/d' -e '/uid:/d' -e '/creationTimestamp:/d' | \
		kubectl apply -n speech -f - 2>/dev/null || echo "⚠️  ConfigMap not copied to speech namespace"
	@kubectl get secret friend-lite-secrets -n $(APPLICATION_NAMESPACE) -o yaml | \
		sed -e '/namespace:/d' -e '/resourceVersion:/d' -e '/uid:/d' -e '/creationTimestamp:/d' | \
		kubectl apply -n speech -f - 2>/dev/null || echo "⚠️  Secret not copied to speech namespace"
	@echo "✅ Kubernetes configuration files generated"

config-all: config-docker config-k8s ## Generate all configuration files
	@echo "✅ All configuration files generated"

clean: ## Clean up generated configuration files
	@echo "🧹 Cleaning up generated configuration files..."
	@rm -f backends/advanced/.env
	@rm -f extras/speaker-recognition/.env
	@rm -f extras/openmemory-mcp/.env
	@rm -f extras/asr-services/.env
	@rm -f extras/havpe-relay/.env
	@rm -f backends/simple/.env
	@rm -f backends/other-backends/omi-webhook-compatible/.env
	@rm -f skaffold.env
	@rm -f backends/charts/advanced-backend/templates/env-configmap.yaml
	@echo "✅ Generated files cleaned"

# ========================================
# DEPLOYMENT TARGETS
# ========================================

deploy: ## Deploy using configured deployment mode
	@echo "🚀 Deploying using $(DEPLOYMENT_MODE) mode..."
ifeq ($(DEPLOYMENT_MODE),docker-compose)
	@$(MAKE) deploy-docker
else ifeq ($(DEPLOYMENT_MODE),kubernetes)
	@$(MAKE) deploy-k8s
else
	@echo "❌ Unknown deployment mode: $(DEPLOYMENT_MODE)"
	@exit 1
endif

deploy-docker: config-docker ## Deploy using Docker Compose
	@echo "🐳 Deploying with Docker Compose..."
	@cd backends/advanced && docker-compose up -d
	@echo "✅ Docker Compose deployment completed"

deploy-k8s: config-k8s ## Deploy to Kubernetes using Skaffold
	@echo "☸️  Deploying to Kubernetes with Skaffold..."
	@set -a; source skaffold.env; set +a; skaffold run --profile=advanced-backend --default-repo=$(CONTAINER_REGISTRY)
	@echo "✅ Kubernetes deployment completed"

deploy-k8s-full: deploy-infrastructure deploy-apps ## Deploy infrastructure + applications to Kubernetes
	@echo "✅ Full Kubernetes deployment completed"

deploy-infrastructure: ## Deploy infrastructure services to Kubernetes
	@echo "🏗️  Deploying infrastructure services..."
	@kubectl apply -f k8s-manifests/
	@echo "✅ Infrastructure deployment completed"

deploy-apps: config-k8s ## Deploy application services to Kubernetes
	@echo "📱 Deploying application services..."
	@set -a; source skaffold.env; set +a; skaffold run --profile=advanced-backend --default-repo=$(CONTAINER_REGISTRY)
	@echo "✅ Application deployment completed"

# ========================================
# UTILITY TARGETS
# ========================================

check-infrastructure: ## Check if infrastructure services are running
	@echo "🔍 Checking infrastructure services..."
	@kubectl get pods -n $(INFRASTRUCTURE_NAMESPACE) || echo "❌ Infrastructure namespace not found"
	@kubectl get services -n $(INFRASTRUCTURE_NAMESPACE) || echo "❌ Infrastructure services not found"

check-apps: ## Check if application services are running
	@echo "🔍 Checking application services..."
	@kubectl get pods -n $(APPLICATION_NAMESPACE) || echo "❌ Application namespace not found"
	@kubectl get services -n $(APPLICATION_NAMESPACE) || echo "❌ Application services not found"

# ========================================
# DEVELOPMENT TARGETS
# ========================================

build-backend: ## Build backend Docker image
	@echo "🔨 Building backend Docker image..."
	@cd backends/advanced && docker build -t advanced-backend:latest .

up-backend: config-docker ## Start backend services
	@echo "🚀 Starting backend services..."
	@cd backends/advanced && docker-compose up -d

down-backend: ## Stop backend services
	@echo "🛑 Stopping backend services..."
	@cd backends/advanced && docker-compose down

# ========================================
# KUBERNETES UTILITIES
# ========================================

k8s-status: ## Check Kubernetes cluster status and health
	@echo "📊 Checking Kubernetes cluster status..."
	@$(K8S_SCRIPTS_DIR)/cluster-status.sh

k8s-cleanup: ## Clean up Kubernetes resources and storage
	@echo "🧹 Starting Kubernetes cleanup..."
	@echo "This will help clean up registry storage and unused resources"
	@$(K8S_SCRIPTS_DIR)/cleanup-registry-storage.sh

k8s-purge: ## Purge unused images (registry + container)
	@echo "🗑️  Purging unused images..."
	@$(K8S_SCRIPTS_DIR)/purge-images.sh

# ========================================
# AUDIO MANAGEMENT
# ========================================

audio-manage: ## Interactive audio file management
	@echo "🎵 Starting audio file management..."
	@$(SCRIPTS_DIR)/manage-audio-files.sh

# ========================================
# MYCELIA SYNC
# ========================================

mycelia-sync-status: ## Show Mycelia OAuth sync status for all users
	@echo "📊 Checking Mycelia OAuth sync status..."
	@cd backends/advanced && uv run python scripts/sync_friendlite_mycelia.py --status

mycelia-sync-all: ## Sync all Friend-Lite users to Mycelia OAuth
	@echo "🔄 Syncing all Friend-Lite users to Mycelia OAuth..."
	@echo "⚠️  This will create OAuth credentials for users without them"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@cd backends/advanced && uv run python scripts/sync_friendlite_mycelia.py --sync-all

mycelia-sync-user: ## Sync specific user to Mycelia OAuth (usage: make mycelia-sync-user EMAIL=user@example.com)
	@echo "👤 Syncing specific user to Mycelia OAuth..."
	@if [ -z "$(EMAIL)" ]; then \
		echo "❌ EMAIL parameter is required. Usage: make mycelia-sync-user EMAIL=user@example.com"; \
		exit 1; \
	fi
	@cd backends/advanced && uv run python scripts/sync_friendlite_mycelia.py --email $(EMAIL)

mycelia-check-orphans: ## Find Mycelia objects without Friend-Lite owner
	@echo "🔍 Checking for orphaned Mycelia objects..."
	@cd backends/advanced && uv run python scripts/sync_friendlite_mycelia.py --check-orphans

mycelia-reassign-orphans: ## Reassign orphaned objects to user (usage: make mycelia-reassign-orphans EMAIL=admin@example.com)
	@echo "♻️  Reassigning orphaned Mycelia objects..."
	@if [ -z "$(EMAIL)" ]; then \
		echo "❌ EMAIL parameter is required. Usage: make mycelia-reassign-orphans EMAIL=admin@example.com"; \
		exit 1; \
	fi
	@echo "⚠️  This will reassign all orphaned objects to: $(EMAIL)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@cd backends/advanced && uv run python scripts/sync_friendlite_mycelia.py --reassign-orphans --target-email $(EMAIL)

# ========================================
# TESTING TARGETS
# ========================================

# Define test environment variables
TEST_ENV := BACKEND_URL=http://localhost:8001 ADMIN_EMAIL=test-admin@example.com ADMIN_PASSWORD=test-admin-password-123

test-robot: ## Run all Robot Framework tests
	@echo "🧪 Running all Robot Framework tests..."
	@cd tests && $(TEST_ENV) robot --outputdir ../results .
	@echo "✅ All Robot Framework tests completed"
	@echo "📊 Results available in: results/"

test-robot-integration: ## Run integration tests only
	@echo "🧪 Running Robot Framework integration tests..."
	@cd tests && $(TEST_ENV) robot --outputdir ../results integration/
	@echo "✅ Robot Framework integration tests completed"
	@echo "📊 Results available in: results/"

test-robot-unit: ## Run unit tests only
	@echo "🧪 Running Robot Framework unit tests..."
	@cd tests && $(TEST_ENV) robot --outputdir ../results unit/ || echo "⚠️  No unit tests directory found"
	@echo "✅ Robot Framework unit tests completed"
	@echo "📊 Results available in: results/"

test-robot-endpoints: ## Run endpoint tests only
	@echo "🧪 Running Robot Framework endpoint tests..."
	@cd tests && $(TEST_ENV) robot --outputdir ../results endpoints/
	@echo "✅ Robot Framework endpoint tests completed"
	@echo "📊 Results available in: results/"

test-robot-specific: ## Run specific Robot Framework test file (usage: make test-robot-specific FILE=path/to/test.robot)
	@echo "🧪 Running specific Robot Framework test: $(FILE)"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ FILE parameter is required. Usage: make test-robot-specific FILE=path/to/test.robot"; \
		exit 1; \
	fi
	@cd tests && $(TEST_ENV) robot --outputdir ../results $(FILE)
	@echo "✅ Robot Framework test completed: $(FILE)"
	@echo "📊 Results available in: results/"

test-robot-clean: ## Clean up Robot Framework test results
	@echo "🧹 Cleaning up Robot Framework test results..."
	@rm -rf results/
	@echo "✅ Test results cleaned"

# ========================================
# MULTI-ENVIRONMENT SUPPORT
# ========================================

env-list: ## List available environments
	@echo "📋 Available Environments:"
	@echo ""
	@ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$$||' | while read env; do \
		echo "  • $$env"; \
		if [ -f "environments/$$env.env" ]; then \
			grep '^# ' environments/$$env.env | head -1 | sed 's/^# /    /'; \
		fi; \
	done
	@echo ""
	@echo "Usage: make env-start ENV=<name>"
	@echo "   or: ./start-env.sh <name> [options]"

env-start: ## Start specific environment (usage: make env-start ENV=dev)
	@if [ -z "$(ENV)" ]; then \
		echo "❌ ENV parameter required"; \
		echo "Usage: make env-start ENV=dev"; \
		echo ""; \
		$(MAKE) env-list; \
		exit 1; \
	fi
	@./start-env.sh $(ENV) $(OPTS)

env-stop: ## Stop specific environment (usage: make env-stop ENV=dev)
	@if [ -z "$(ENV)" ]; then \
		echo "❌ ENV parameter required"; \
		echo "Usage: make env-stop ENV=dev"; \
		exit 1; \
	fi
	@echo "🛑 Stopping environment: $(ENV)"
	@COMPOSE_PROJECT_NAME=friend-lite-$(ENV) docker compose down

env-clean: ## Clean specific environment data (usage: make env-clean ENV=dev)
	@if [ -z "$(ENV)" ]; then \
		echo "❌ ENV parameter required"; \
		echo "Usage: make env-clean ENV=dev"; \
		exit 1; \
	fi
	@echo "⚠️  This will delete all data for environment: $(ENV)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@source environments/$(ENV).env && rm -rf $$DATA_DIR
	@COMPOSE_PROJECT_NAME=friend-lite-$(ENV) docker compose down -v
	@echo "✅ Environment $(ENV) cleaned"

env-status: ## Show status of all environments
	@echo "📊 Environment Status:"
	@echo ""
	@for env in $$(ls -1 environments/*.env 2>/dev/null | sed 's|environments/||;s|.env$$||'); do \
		echo "Environment: $$env"; \
		COMPOSE_PROJECT_NAME=friend-lite-$$env docker compose ps 2>/dev/null | grep -v "NAME" || echo "  Not running"; \
		echo ""; \
	done

