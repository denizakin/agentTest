# Project Vision & Purpose
- It is an evolving auto-trading platform for crypto currencies
- There will be six main scopes
    - Data gathering
    - Data evaluation and strategy creation
    - Back testing for found strategies
    - Strategy optimization
    - Live trading
    - Portfolio management(includes frontend)
- OKX APIs will be used for data gathering and trading

# Project Tools
- Use python for primary language
- Use React+NodeJs for frontend
- Use postgresql+timescaleDB for data storage
- python-okx 0.4.0 is the python library for API usage

# Project Steps

## Data gathering
- Use candlestick data

## Data evaluation
- To be determined later

## Back testing for found strategies
- To be determined later

## Strategy optimization
- To be determined later

## Live trading
- To be determined later

## Portfolio management(includes frontend)
- To be determined later


# Repository Guidelines

## Project Structure & Module Organization
- Place application code under `src/AgentTest` using one project per service or agent.
- Shared libraries go in `src/Common`. 
- Integration and unit tests belong in `tests/AgentTest.Tests`. 
- Config files and JSON fixtures live in `resources/`. 
- Keep sensitive environment values outside source control; copy `resources/.env.example` to `resources/.env` locally.
- Keep generated artifacts out of source control by adding them to `.gitignore`.

## Coding Style & Naming Conventions
- Follow standard Python style (PEP 8):
    - PascalCase for classes and public interfaces.
    - snake_case for functions, locals, and parameters.
    - ALL_CAPS only for constants and environment variables.
- Keep files encoded as UTF-8.
- Limit agents to single-responsibility classes and document public APIs with docstrings.

## Testing Guidelines
- Use pytest for unit tests in `tests/AgentTest.Tests` following the `test_<subject>_should_<expected_behavior>` naming pattern.
- Mirror the production package structure under `tests/` to simplify discovery.
- Place integration tests that touch external services in `tests/AgentTest.Integration`.
- Target at least 80% line coverage for new modules and document any justified gaps in the pull request description.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes (e.g., `feat:`, `fix:`, `chore:`) and keep subject lines under 72 characters. 
- Push descriptive branches like `feature/agent-retry-policy`. 
- Each pull request must include a summary, linked issue or ticket reference, and validation notes (e.g., `pytest` output). 
- Add screenshots or logs when UI or CLI behavior changes. Request review from another agent and ensure all checks pass before merging.
