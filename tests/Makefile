# Chronicle Test Makefile
# Shortcuts for running tests and managing test containers

.PHONY: help all clean \
        containers-start containers-stop containers-restart containers-rebuild \
        containers-start-rebuild containers-clean containers-status containers-logs \
        start stop restart rebuild start-rebuild status logs \
        test test-quick test-slow test-sdk test-all-with-slow-and-sdk clean-all

# Default output directory
OUTPUTDIR ?= results
TEST_DIR = endpoints integration infrastructure
SERVICE ?= chronicle-backend-test

help:
	@echo "Chronicle Test Targets:"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make test          - Start containers + run all tests (excludes slow/sdk)"
	@echo "  make test-quick    - Run tests on existing containers"
	@echo "  make start         - Start test containers"
	@echo "  make stop          - Stop containers (keep volumes)"
	@echo "  make restart       - Restart containers (for .env changes)"
	@echo "  make rebuild       - Rebuild images only (doesn't start)"
	@echo "  make start-rebuild - Stop + rebuild + start (for code changes)"
	@echo "  make status        - Show container status"
	@echo ""
	@echo "Running Tests:"
	@echo "  make all         - Run all tests (excludes slow/sdk)"
	@echo "  make endpoints   - Run only endpoint tests"
	@echo "  make integration - Run only integration tests"
	@echo "  make infra       - Run only infrastructure tests"
	@echo ""
	@echo "Special Test Tags:"
	@echo "  make test-slow                    - Run ONLY slow tests (backend restarts)"
	@echo "  make test-sdk                     - Run ONLY SDK tests (unreleased)"
	@echo "  make test-all-with-slow-and-sdk   - Run ALL tests including excluded"
	@echo ""
	@echo "Container Management:"
	@echo "  make containers-start         - Start test containers"
	@echo "  make containers-stop          - Stop containers (keep volumes)"
	@echo "  make containers-restart       - Restart containers (config changes)"
	@echo "  make containers-rebuild       - Rebuild images only"
	@echo "  make containers-start-rebuild - Stop + rebuild + start (code changes)"
	@echo "  make containers-clean         - Save logs + remove everything"
	@echo "  make containers-status        - Show container health"
	@echo "  make containers-logs          - View service logs (use SERVICE=name)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Remove test output files"
	@echo "  make clean-all   - Clean results + containers (saves logs)"
	@echo ""
	@echo "Environment Variables:"
	@echo "  OUTPUTDIR        - Output directory (default: results)"
	@echo "  SERVICE          - Service name for logs (default: chronicle-backend-test)"
	@echo ""
	@echo "Examples:"
	@echo "  make test                                  # Full workflow"
	@echo "  make endpoints                             # Only endpoint tests"
	@echo "  make start-rebuild                         # After code changes"
	@echo "  make containers-logs SERVICE=workers-test  # View worker logs"

# Run all tests (excludes slow and sdk tests for faster feedback)
# Creates a persistent fixture conversation that won't be deleted between suites
all:
	@echo "Running all tests (excluding slow and sdk tests)..."
	CREATE_FIXTURE=true uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "All Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		--exclude slow \
		--exclude sdk \
		$(TEST_DIR)

# Run only endpoint tests
endpoints:
	@echo "Running endpoint tests..."
	uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "Endpoint Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		endpoints

# Run only integration tests
integration:
	@echo "Running integration tests..."
	CREATE_FIXTURE=true uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "Integration Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		integration

# Run only infrastructure tests
infra:
	@echo "Running infrastructure tests..."
	uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "Infrastructure Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		infrastructure

# Clean up test output files
clean:
	@echo "Cleaning test outputs..."
	rm -f output.xml log.html report.html
	rm -rf $(OUTPUTDIR)
	@echo "Clean complete!"

# ============================================================================
# Container Management Targets
# ============================================================================

# Start test containers
containers-start:
	@./bin/start-containers.sh

# Stop test containers (preserve volumes)
containers-stop:
	@./bin/stop-containers.sh

# Restart test containers
containers-restart:
	@./bin/restart-containers.sh

# Rebuild test containers (images only)
containers-rebuild:
	@./bin/rebuild-containers.sh

# Stop, rebuild, and start test containers
containers-start-rebuild:
	@./bin/start-rebuild-containers.sh

# Clean test containers (ALWAYS saves logs first!)
containers-clean:
	@./bin/clean-containers.sh

# Show container status
containers-status:
	@./bin/status-containers.sh

# View container logs
containers-logs:
	@./bin/logs-containers.sh $(SERVICE)

# ============================================================================
# Convenient Aliases
# ============================================================================

start: containers-start
stop: containers-stop
restart: containers-restart
rebuild: containers-rebuild
start-rebuild: containers-start-rebuild
status: containers-status
logs: containers-logs

# ============================================================================
# Combined Workflows
# ============================================================================

# Full workflow: start containers + run all tests
test: containers-start all

# Quick workflow: run tests on existing containers
test-quick: all

# Run ONLY slow tests (backend restarts, long timeouts)
test-slow:
	@echo "Running slow tests only..."
	uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "Slow Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		--include slow \
		$(TEST_DIR)

# Run ONLY SDK tests (unreleased SDK features)
test-sdk:
	@echo "Running SDK tests only..."
	CREATE_FIXTURE=true uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "SDK Tests" \
		--console verbose \
		--loglevel INFO:INFO \
		--include sdk \
		$(TEST_DIR)

# Run ALL tests including slow and SDK tests
test-all-with-slow-and-sdk:
	@echo "Running ALL tests including slow and SDK tests..."
	CREATE_FIXTURE=true uv run --with-requirements test-requirements.txt robot --outputdir $(OUTPUTDIR) \
		--name "All Tests (Including Slow and SDK)" \
		--console verbose \
		--loglevel INFO:INFO \
		$(TEST_DIR)

# Complete cleanup: test results + containers (saves logs)
clean-all: clean containers-clean
