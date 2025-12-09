#!/bin/bash
set -e

# Friend-Lite Dependency Installation Script
# Installs all required dependencies for running Friend-Lite
# Works on Ubuntu/Debian-based systems (including WSL2)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Friend-Lite Dependency Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This script will install:"
echo "  • Git (version control)"
echo "  • Make (build automation)"
echo "  • curl (HTTP client)"
echo "  • Docker & Docker Compose (container platform)"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        echo "❌ Cannot detect Linux distribution"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported operating system: $OSTYPE"
    echo "This script supports Ubuntu/Debian and macOS only"
    exit 1
fi

echo "📋 Detected OS: $OS"
echo ""

# Check if running in WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "🪟 Running in WSL (Windows Subsystem for Linux)"
    IN_WSL=true
else
    IN_WSL=false
fi
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install packages on Ubuntu/Debian
install_ubuntu_deps() {
    echo "📦 Installing dependencies for Ubuntu/Debian..."
    echo ""

    # Update package lists
    echo "📥 Updating package lists..."
    sudo apt-get update -qq
    echo "✅ Package lists updated"
    echo ""

    # Install basic tools
    echo "🔧 Installing basic tools (git, make, curl)..."
    sudo apt-get install -y git make curl wget ca-certificates gnupg lsb-release
    echo "✅ Basic tools installed"
    echo ""

    # Check if Docker is already installed
    if command_exists docker; then
        echo "ℹ️  Docker is already installed"
        docker --version
    else
        # Check if we're in WSL - Docker Desktop is preferred there
        if [ "$IN_WSL" = true ]; then
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🪟 WSL DETECTED - Docker Installation Options"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "You have two options for Docker on WSL:"
            echo ""
            echo "1. Docker Desktop (Recommended)"
            echo "   • GUI application on Windows"
            echo "   • Easiest to manage containers"
            echo "   • Shared daemon between Windows and WSL"
            echo "   • Download: https://www.docker.com/products/docker-desktop"
            echo ""
            echo "2. Docker Engine in WSL (Advanced)"
            echo "   • Command-line only"
            echo "   • Lighter weight (no GUI)"
            echo "   • Runs entirely in WSL"
            echo ""
            read -p "Install Docker Engine in WSL? (y/N): " install_docker

            if [ "$install_docker" = "y" ] || [ "$install_docker" = "Y" ]; then
                echo ""
                echo "🐳 Installing Docker Engine in WSL..."

                # Add Docker's official GPG key
                sudo mkdir -p /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

                # Set up Docker repository
                echo \
                  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

                # Install Docker Engine
                sudo apt-get update -qq
                sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

                # Add current user to docker group
                sudo usermod -aG docker $USER

                # Start Docker service
                sudo service docker start

                echo "✅ Docker Engine installed in WSL"
                echo ""
                echo "⚠️  IMPORTANT: You need to log out and log back in for group changes to take effect"
                echo "   Or run: newgrp docker"
                echo ""
            else
                echo ""
                echo "ℹ️  Skipping Docker installation"
                echo "   Please install Docker Desktop for Windows, then:"
                echo "   1. Open Docker Desktop Settings"
                echo "   2. Go to Resources → WSL Integration"
                echo "   3. Enable integration with Ubuntu"
                echo ""
            fi
        else
            # Native Linux - install Docker Engine
            echo "🐳 Installing Docker Engine..."

            # Add Docker's official GPG key
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

            # Set up Docker repository
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
              $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

            # Install Docker Engine
            sudo apt-get update -qq
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

            # Add current user to docker group
            sudo usermod -aG docker $USER

            # Start Docker service
            sudo systemctl start docker
            sudo systemctl enable docker

            echo "✅ Docker Engine installed"
            echo ""
            echo "⚠️  IMPORTANT: You need to log out and log back in for group changes to take effect"
            echo "   Or run: newgrp docker"
            echo ""
        fi
    fi
}

# Function to install packages on macOS
install_macos_deps() {
    echo "📦 Installing dependencies for macOS..."
    echo ""

    # Check if Homebrew is installed
    if ! command_exists brew; then
        echo "🍺 Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "✅ Homebrew installed"
        echo ""
    else
        echo "✅ Homebrew is already installed"
        echo ""
    fi

    # Install basic tools
    echo "🔧 Installing basic tools..."
    brew install git make curl
    echo "✅ Basic tools installed"
    echo ""

    # Check if Docker Desktop is installed
    if command_exists docker; then
        echo "ℹ️  Docker is already installed"
        docker --version
    else
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🐳 Docker Installation Required"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Docker Desktop is required for Friend-Lite on macOS."
        echo ""
        echo "Options:"
        echo "  1. Download manually: https://www.docker.com/products/docker-desktop"
        echo "  2. Install via Homebrew: brew install --cask docker"
        echo ""
        read -p "Install Docker Desktop via Homebrew? (y/N): " install_docker

        if [ "$install_docker" = "y" ] || [ "$install_docker" = "Y" ]; then
            echo ""
            echo "🐳 Installing Docker Desktop..."
            brew install --cask docker
            echo ""
            echo "✅ Docker Desktop installed"
            echo ""
            echo "⚠️  IMPORTANT: Open Docker Desktop from Applications to start Docker"
        else
            echo ""
            echo "ℹ️  Please install Docker Desktop manually before continuing"
        fi
    fi
}

# Install dependencies based on OS
case $OS in
    ubuntu|debian)
        install_ubuntu_deps
        ;;
    macos)
        install_macos_deps
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        echo "This script supports Ubuntu, Debian, and macOS"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Dependency Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Installed tools:"
echo ""

# Verify installations
if command_exists git; then
    echo "  ✅ Git:            $(git --version | cut -d' ' -f3)"
else
    echo "  ❌ Git:            Not found"
fi

if command_exists make; then
    echo "  ✅ Make:           $(make --version | head -n1 | cut -d' ' -f3)"
else
    echo "  ❌ Make:           Not found"
fi

if command_exists curl; then
    echo "  ✅ curl:           $(curl --version | head -n1 | cut -d' ' -f2)"
else
    echo "  ❌ curl:           Not found"
fi

if command_exists docker; then
    echo "  ✅ Docker:         $(docker --version | cut -d' ' -f3 | tr -d ',')"
else
    echo "  ❌ Docker:         Not found"
fi

if command_exists docker && docker compose version >/dev/null 2>&1; then
    echo "  ✅ Docker Compose: $(docker compose version | cut -d' ' -f4)"
else
    echo "  ❌ Docker Compose: Not found"
fi

echo ""

# Check if Docker is accessible
if command_exists docker; then
    if docker ps >/dev/null 2>&1; then
        echo "✅ Docker is running and accessible"
    else
        echo "⚠️  Docker is installed but not accessible"
        echo ""
        if [ "$IN_WSL" = true ]; then
            echo "💡 If you installed Docker Desktop on Windows:"
            echo "   1. Make sure Docker Desktop is running"
            echo "   2. Open Docker Desktop Settings → Resources → WSL Integration"
            echo "   3. Enable Ubuntu-22.04"
            echo "   4. Click 'Apply & Restart'"
        else
            echo "💡 You may need to:"
            echo "   1. Log out and log back in (for group permissions)"
            echo "   2. Or run: newgrp docker"
            echo "   3. Or start Docker: sudo systemctl start docker"
        fi
    fi
else
    echo "⚠️  Docker is not installed"
    echo ""
    if [ "$IN_WSL" = true ]; then
        echo "💡 For WSL, we recommend Docker Desktop for Windows"
        echo "   Download: https://www.docker.com/products/docker-desktop"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Run the Friend-Lite setup wizard:"
echo "  make wizard"
echo ""
echo "Or set up components individually:"
echo "  make setup-secrets      # Configure API keys"
echo "  make setup-environment  # Create environment"
echo "  ./start-env.sh dev      # Start Friend-Lite"
echo ""
