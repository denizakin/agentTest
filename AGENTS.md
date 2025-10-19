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
- Use sqlalchemy as ORM
    - Keep db versioning

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
- Shared libraries go in `src/Common`. 
- Config files and JSON fixtures live in `resources/`. 
- Keep sensitive environment values outside source control;
    - Use `resources/.env` and keep it locally.
- Keep generated artifacts out of source control by adding them to `.gitignore`.
- Source python code live in src folder
    - API helper files should be in src/api
    - DB helper files should be in src/db
    - DB poco classes should be in src/db/poco

## Coding Style & Naming Conventions
- Follow standard Python style (PEP 8):
    - PascalCase for classes and public interfaces.
    - snake_case for functions, locals, and parameters.
    - ALL_CAPS only for constants and environment variables.
- Keep files encoded as UTF-8.
- Limit agents to single-responsibility classes and document public APIs with docstrings.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes (e.g., `feat:`, `fix:`, `chore:`) and keep subject lines under 72 characters. 
- Push descriptive branches like `feature/agent-retry-policy`. 
- Each pull request must include a summary, linked issue or ticket reference, and validation notes (e.g., `pytest` output). 
- Add screenshots or logs when UI or CLI behavior changes. Request review from another agent and ensure all checks pass before merging.
