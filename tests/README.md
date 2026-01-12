# Chronicle Test Suite

Quick reference guide for running Robot Framework tests locally.

## Quick Start

### Run Tests Without API Keys (Fast)
```bash
cd tests
./run-no-api-tests.sh
```
- **Runs**: ~70% of test suite (excludes `requires-api-keys` tag)
- **Config**: `configs/mock-services.yml` (no external APIs)
- **Time**: ~10-15 minutes
- **Use**: Daily development, PR validation

### Run Full Test Suite (Comprehensive)
```bash
# Set API keys first
export DEEPGRAM_API_KEY=your-deepgram-key
export OPENAI_API_KEY=your-openai-key

cd tests
./run-robot-tests.sh
```
- **Runs**: 100% of test suite (all tests)
- **Config**: `configs/deepgram-openai.yml` (with external APIs)
- **Time**: ~20-30 minutes
- **Use**: Before pushing to dev/main, testing API integrations

## Test Categories

### No API Keys Required (~70%)
- **Endpoint Tests**: Auth, CRUD operations, permissions
- **Infrastructure Tests**: Worker management, queue operations
- **Health Tests**: System health and readiness checks
- **Basic Integration**: Non-transcription workflows

### API Keys Required (~30%)
Tagged with `requires-api-keys`:
- **Audio Upload Tests**: File processing with transcription
- **Memory Tests**: LLM-based memory operations
- **Audio Streaming**: Real-time transcription tests
- **E2E Integration**: Full pipeline with transcription and memory

## Configuration Files

### `configs/mock-services.yml`
- No external API calls
- Dummy LLM/embedding models (satisfy config requirements)
- Used by: `run-no-api-tests.sh`
- Perfect for: Endpoint and infrastructure testing

### `configs/deepgram-openai.yml`
- Real Deepgram transcription
- Real OpenAI LLM and embeddings
- Used by: `run-robot-tests.sh`
- Perfect for: Full E2E validation

### `configs/parakeet-ollama.yml`
- Local Parakeet ASR (offline transcription)
- Local Ollama LLM (offline processing)
- Perfect for: Fully offline testing

## Environment Configuration

Tests use isolated test environment with separate ports and database:

```bash
# Test Ports (avoid conflicts with dev services)
Backend:  8001 (vs 8000 prod)
MongoDB:  27018 (vs 27017 prod)
Qdrant:   6337/6338 (vs 6333/6334 prod)
WebUI:    3001 (vs 5173 prod)

# Test Database
Database: test_db (separate from production)
```

### Test Credentials
```bash
# Admin account (created automatically)
ADMIN_EMAIL=test-admin@example.com
ADMIN_PASSWORD=test-admin-password-123

# Authentication secret (test-specific)
AUTH_SECRET_KEY=test-jwt-signing-key-for-integration-tests
```

## Test Scripts

### `run-no-api-tests.sh`
- Excludes tests tagged with `requires-api-keys`
- Uses `configs/mock-services.yml`
- No API key validation
- Fast feedback loop

### `run-robot-tests.sh`
- Runs all tests (including API-dependent)
- Uses `configs/deepgram-openai.yml`
- Validates API keys before execution
- Comprehensive test coverage

### `run-api-tests.sh` (Optional)
- Runs only tests tagged with `requires-api-keys`
- Validates API integrations specifically
- ~30% of test suite

## Quick Command Reference

```bash
# No-API tests (fast)
cd tests && ./run-no-api-tests.sh

# Full tests (comprehensive)
export DEEPGRAM_API_KEY=xxx OPENAI_API_KEY=yyy
cd tests && ./run-robot-tests.sh

# Run specific suites
make endpoints
make integration
make infra

# View results
open results-no-api/report.html
open results/log.html

# Clean up
docker compose -f ../backends/advanced/docker-compose-test.yml down -v
```

## Additional Resources

- **TESTING_GUIDELINES.md**: Comprehensive testing patterns and rules
- **tags.md**: Approved tag list (12 tags only)
- **setup/test_env.py**: Test environment configuration
- **setup/test_data.py**: Test data and fixtures
