from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


class StrategyManager:
    """Manages dynamic strategy registration: writes code to file and updates registry."""

    def __init__(self, strategies_dir: Optional[Path] = None):
        if strategies_dir is None:
            # Default to the strategies directory
            strategies_dir = Path(__file__).parent
        self.strategies_dir = strategies_dir
        self.registry_file = strategies_dir / "registry.py"

    def register_strategy(self, name: str, code: str, class_name: str) -> None:
        """
        Register a new strategy by:
        1. Writing code to a .py file in strategies directory
        2. Adding import and registry entry to registry.py

        Args:
            name: Strategy key for registry (e.g., "my_strategy")
            code: Python code containing the strategy class
            class_name: Name of the strategy class (e.g., "MyStrategy")
        """
        # Sanitize name for filename (alphanumeric and underscore only)
        safe_name = re.sub(r'[^a-z0-9_]', '', name.lower())
        if not safe_name:
            raise ValueError(f"Invalid strategy name: {name}")

        # Write strategy code to file
        strategy_file = self.strategies_dir / f"{safe_name}.py"
        strategy_file.write_text(code, encoding="utf-8")

        # Update registry.py
        self._update_registry(safe_name, class_name)

    def _update_registry(self, module_name: str, class_name: str) -> None:
        """Update registry.py to import and register the new strategy."""
        registry_content = self.registry_file.read_text(encoding="utf-8")

        # 1. Add import statement after existing strategy imports
        import_line = f"from .{module_name} import {class_name}"

        # Find the last strategy import line
        import_pattern = r"from \.\w+ import \w+Strategy"
        matches = list(re.finditer(import_pattern, registry_content))

        if matches:
            # Insert after the last import
            last_import = matches[-1]
            insert_pos = last_import.end()
            # Find the end of line
            eol = registry_content.find('\n', insert_pos)
            if eol == -1:
                eol = len(registry_content)

            registry_content = (
                registry_content[:eol] +
                f"\n{import_line}" +
                registry_content[eol:]
            )
        else:
            # No imports found, add after the typing imports
            typing_end = registry_content.find("import backtrader as bt")
            if typing_end != -1:
                eol = registry_content.find('\n', typing_end)
                registry_content = (
                    registry_content[:eol] +
                    f"\n\n# Import and register available strategies here\n{import_line}" +
                    registry_content[eol:]
                )

        # 2. Add registry entry
        # Find the STRATEGY_REGISTRY dict closing brace
        registry_pattern = r'(STRATEGY_REGISTRY:\s*Dict\[str,\s*Type\[bt\.Strategy\]\]\s*=\s*\{[^}]*)'
        match = re.search(registry_pattern, registry_content, re.DOTALL)

        if match:
            dict_content = match.group(1)
            # Check if already registered
            if f'"{module_name}"' in dict_content:
                return  # Already registered

            # Find the last entry before closing brace
            # Add new entry before the closing brace
            closing_brace = registry_content.find('}', match.end())
            if closing_brace != -1:
                # Find the last comma or opening brace
                insert_point = closing_brace
                # Look backwards for the last entry
                before_brace = registry_content[:closing_brace].rstrip()

                # Add comma if needed
                if before_brace.endswith(','):
                    new_entry = f'\n    "{module_name}": {class_name},'
                elif before_brace.endswith('{'):
                    new_entry = f'\n    "{module_name}": {class_name},'
                else:
                    new_entry = f',\n    "{module_name}": {class_name},'

                registry_content = (
                    registry_content[:insert_point] +
                    new_entry +
                    registry_content[insert_point:]
                )

        # Write updated registry
        self.registry_file.write_text(registry_content, encoding="utf-8")

    def unregister_strategy(self, name: str) -> None:
        """
        Remove a strategy by:
        1. Deleting the .py file
        2. Removing import and registry entry from registry.py
        """
        safe_name = re.sub(r'[^a-z0-9_]', '', name.lower())

        # Delete strategy file
        strategy_file = self.strategies_dir / f"{safe_name}.py"
        if strategy_file.exists():
            strategy_file.unlink()

        # Update registry.py
        registry_content = self.registry_file.read_text(encoding="utf-8")

        # Remove import line
        import_pattern = rf"from \.{safe_name} import \w+\n"
        registry_content = re.sub(import_pattern, "", registry_content)

        # Remove registry entry
        entry_pattern = rf'\s*"{safe_name}":\s*\w+,?\n'
        registry_content = re.sub(entry_pattern, "", registry_content)

        # Write updated registry
        self.registry_file.write_text(registry_content, encoding="utf-8")
