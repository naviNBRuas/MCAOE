# Contributing to MCAOE

Thank you for your interest in contributing to MCAOE. Please follow these guidelines:

1. Fork the repository and create a feature branch.
2. Run tests and linting locally before submitting a pull request.
3. Keep changes focused and add tests for new behavior.
4. No secrets or API keys should be committed. Use the OS keyring or environment variables.
5. Describe your changes in the PR and reference any related issues.

If you're adding a new plugin or parser, follow the existing plugin patterns in `src/mcaoe/plugins` and add tests under `tests/`.
