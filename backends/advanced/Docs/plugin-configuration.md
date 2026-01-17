# Plugin Configuration Architecture

Chronicle uses a clean separation of concerns for plugin configuration, dividing settings across three locations based on their purpose.

## Configuration Files

### 1. `config/plugins.yml` - Orchestration Only

**Purpose**: Controls which plugins are enabled and what events they listen to

**Contains**:
- Plugin enable/disable flags
- Event subscriptions
- Trigger conditions (wake words, etc.)

**Example**:
```yaml
plugins:
  email_summarizer:
    enabled: true
    events:
      - conversation.complete
    condition:
      type: always

  homeassistant:
    enabled: false
    events:
      - transcript.streaming
    condition:
      type: wake_word
      wake_words:
        - hey vivi
```

### 2. `backends/advanced/src/advanced_omi_backend/plugins/{plugin_id}/config.yml` - Plugin Settings

**Purpose**: Plugin-specific non-secret configuration

**Contains**:
- Feature flags
- Timeouts and limits
- Display preferences
- References to environment variables using `${VAR_NAME}` syntax

**Example** (`plugins/email_summarizer/config.yml`):
```yaml
# Email content settings
subject_prefix: "Conversation Summary"
summary_max_sentences: 3
include_conversation_id: true

# SMTP config (reads from .env)
smtp_host: ${SMTP_HOST}
smtp_port: ${SMTP_PORT:-587}
smtp_username: ${SMTP_USERNAME}
smtp_password: ${SMTP_PASSWORD}
```

### 3. `backends/advanced/.env` - Secrets Only

**Purpose**: All secret values (API keys, passwords, tokens)

**Contains**:
- API keys
- Authentication tokens
- SMTP credentials
- Database passwords

**Example**:
```bash
# Email Summarizer Plugin
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here

# Home Assistant Plugin
HA_URL=http://homeassistant.local:8123
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Configuration Loading Process

When a plugin is initialized, Chronicle merges configuration from all three sources:

```
1. Load plugins/{plugin_id}/config.yml
   ↓
2. Expand ${ENV_VAR} references from .env
   ↓
3. Merge orchestration settings from config/plugins.yml
   ↓
4. Pass complete config to plugin constructor
```

### Example Configuration Flow

**Email Summarizer Plugin**:

1. **Load** `plugins/email_summarizer/config.yml`:
   ```yaml
   subject_prefix: "Conversation Summary"
   smtp_host: ${SMTP_HOST}
   smtp_password: ${SMTP_PASSWORD}
   ```

2. **Expand env vars** from `.env`:
   ```yaml
   subject_prefix: "Conversation Summary"
   smtp_host: "smtp.gmail.com"          # ← Expanded
   smtp_password: "app-password-123"    # ← Expanded
   ```

3. **Merge orchestration** from `config/plugins.yml`:
   ```yaml
   enabled: true                        # ← Added
   events: ["conversation.complete"]    # ← Added
   condition: {type: "always"}          # ← Added
   subject_prefix: "Conversation Summary"
   smtp_host: "smtp.gmail.com"
   smtp_password: "app-password-123"
   ```

4. **Pass to plugin** constructor with complete config

## Environment Variable Expansion

Plugin config files use `${VAR_NAME}` syntax for environment variable references:

- **Simple reference**: `${SMTP_HOST}` → expands to env value
- **With default**: `${SMTP_PORT:-587}` → uses 587 if SMTP_PORT not set
- **Missing vars**: Logs warning and keeps placeholder

**Example**:
```yaml
# In plugin config.yml
smtp_host: ${SMTP_HOST}
smtp_port: ${SMTP_PORT:-587}
timeout: ${HA_TIMEOUT:-30}

# With .env:
# SMTP_HOST=smtp.gmail.com
# (SMTP_PORT not set)
# HA_TIMEOUT=60

# Results in:
# smtp_host: "smtp.gmail.com"
# smtp_port: "587"           # ← Used default
# timeout: "60"              # ← From .env
```

## Creating a New Plugin

To add a new plugin with proper configuration:

### 1. Create plugin directory structure

```bash
backends/advanced/src/advanced_omi_backend/plugins/my_plugin/
├── __init__.py           # Export plugin class
├── plugin.py             # Plugin implementation
└── config.yml            # Plugin-specific config
```

### 2. Add plugin config file

**`plugins/my_plugin/config.yml`**:
```yaml
# My Plugin Configuration
# Non-secret settings only

# Feature settings
feature_enabled: true
timeout: ${MY_PLUGIN_TIMEOUT:-30}

# API configuration (secrets from .env)
api_url: ${MY_PLUGIN_API_URL}
api_key: ${MY_PLUGIN_API_KEY}
```

### 3. Add secrets to `.env.template`

**`backends/advanced/.env.template`**:
```bash
# My Plugin
MY_PLUGIN_API_URL=https://api.example.com
MY_PLUGIN_API_KEY=
MY_PLUGIN_TIMEOUT=30
```

### 4. Add orchestration settings

**`config/plugins.yml`**:
```yaml
plugins:
  my_plugin:
    enabled: false
    events:
      - conversation.complete
    condition:
      type: always
```

### 5. Implement plugin class

**`plugins/my_plugin/plugin.py`**:
```python
from ..base import BasePlugin, PluginContext, PluginResult

class MyPlugin(BasePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Config automatically merged from all sources
        self.api_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.timeout = config.get('timeout', 30)

    async def initialize(self):
        # Plugin initialization
        pass

    async def on_conversation_complete(self, context: PluginContext):
        # Event handler
        pass
```

## Benefits of This Architecture

✅ **Clean separation**: Secrets (.env) vs Config (yml) vs Orchestration (plugins.yml)

✅ **Plugin portability**: Each plugin has self-contained config.yml

✅ **No secret duplication**: Secrets only in .env, referenced via ${VAR}

✅ **Easy discovery**: Want to configure a plugin? → `plugins/{plugin_id}/config.yml`

✅ **Main config.yml stays clean**: No plugin pollution in main backend config

✅ **Unified interface**: All plugins loaded with same pattern via `load_plugin_config()`

## Migration from Old System

If you have existing plugins using the old configuration system:

**Old way** (everything in `config/plugins.yml`):
```yaml
plugins:
  email_summarizer:
    enabled: true
    events: [...]
    subject_prefix: "Summary"          # ❌ Config mixed with orchestration
    smtp_host: smtp.gmail.com          # ❌ Non-secret in wrong place
    smtp_password: app-password        # ❌ SECRET IN VERSION CONTROL!
```

**New way** (properly separated):

1. **Orchestration** in `config/plugins.yml`:
   ```yaml
   plugins:
     email_summarizer:
       enabled: true
       events: [conversation.complete]
   ```

2. **Settings** in `plugins/email_summarizer/config.yml`:
   ```yaml
   subject_prefix: "Summary"
   smtp_host: ${SMTP_HOST}
   smtp_password: ${SMTP_PASSWORD}
   ```

3. **Secrets** in `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PASSWORD=app-password
   ```

## Troubleshooting

### Plugin not loading

**Check logs** for:
- "Plugin 'X' not found" → Directory/file structure issue
- "Environment variable 'X' not found" → Missing .env entry
- "Failed to load config.yml" → YAML syntax error

**Verify**:
```bash
# Check plugin directory exists
ls backends/advanced/src/advanced_omi_backend/plugins/my_plugin/

# Validate config.yml syntax
python -c "import yaml; yaml.safe_load(open('plugins/my_plugin/config.yml'))"

# Check .env has required vars
grep MY_PLUGIN .env
```

### Environment variables not expanding

**Problem**: `${SMTP_HOST}` stays as literal text

**Solution**:
- Ensure `.env` file exists in `backends/advanced/.env`
- Check variable name matches exactly (case-sensitive)
- Restart backend after .env changes
- Check logs for "Environment variable 'X' not found" warnings

### Plugin enabled but not running

**Check**:
1. `config/plugins.yml` has `enabled: true`
2. Plugin subscribed to correct events
3. Conditions are met (wake words, etc.)
4. Plugin initialized without errors (check logs)

## See Also

- [CLAUDE.md](../../../CLAUDE.md) - Main documentation
- [Plugin Development Guide](plugin-development.md) - Creating custom plugins
- [Environment Variables](environment-variables.md) - Complete .env reference
