"""Configuration loading and validation."""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Python 3.11+ has tomllib built-in, older versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class ViewConfig:
    """Configuration for a single view."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize view configuration.

        Args:
            data: Dictionary containing view configuration
        """
        self.title = data.get("title")
        self.view_id = data.get("view_id")
        self.filter = data.get("filter")
        self.graphql_query = data.get("graphql_query")

        # Validate: must have either title or view_id
        if not self.title and not self.view_id:
            raise ValueError("View must have either 'title' or 'view_id'")

        # Validate: must have either filter or graphql_query
        if not self.filter and not self.graphql_query:
            raise ValueError("View must have either 'filter' or 'graphql_query'")

        # Validate: cannot have both filter and graphql_query
        if self.filter and self.graphql_query:
            raise ValueError("View cannot have both 'filter' and 'graphql_query'")

    def __repr__(self):
        identifier = self.title or self.view_id
        return f"ViewConfig({identifier})"


class Config:
    """Application configuration."""

    def __init__(self, config_path: Path):
        """Load and validate configuration.

        Args:
            config_path: Path to config.toml file
        """
        self.config_path = config_path

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load TOML
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Parse Linear config
        linear_config = data.get("linear", {})
        self.api_token = linear_config.get("api_token")

        # Parse views
        views_data = data.get("views", [])
        if not views_data:
            raise ValueError("No views configured. Add [[views]] sections to config.toml")

        self.views = [ViewConfig(view_data) for view_data in views_data]

    def __repr__(self):
        return f"Config({self.config_path}, {len(self.views)} views)"


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Path to config file. Defaults to ./config.toml

    Returns:
        Loaded configuration object
    """
    if config_path is None:
        config_path = Path("config.toml")

    return Config(config_path)
