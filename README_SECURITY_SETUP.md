# Secure API Key Setup (recommended)

- Prefer the OS keyring (macOS Keychain, Windows Credential Manager, or Secret Service on Linux).
- Use the provided helper to store your key:

```py
from mcaoe.ai.provider import store_api_key_in_keyring
store_api_key_in_keyring('gemini', '<YOUR_KEY>')
```

- For CI, set secrets through the CI provider's secret store and expose them as environment variables (e.g., `MCAOE_GEMINI_API_KEY`).
- Do NOT commit any `.env` file containing secrets.
