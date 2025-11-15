"""Export initiatives to various formats."""
import csv
import json
import sys
from typing import List, Dict, Any, TextIO
from datetime import datetime


class InitiativeExporter:
    """Handles exporting initiatives to various formats."""

    # Define the fields to export and their display names
    EXPORT_FIELDS = [
        ("id", "ID"),
        ("name", "Name"),
        ("description", "Description"),
        ("status", "Status"),
        ("sortOrder", "Sort Order"),
        ("startedAt", "Started At"),
        ("targetDate", "Target Date"),
        ("completedAt", "Completed At"),
        ("createdAt", "Created At"),
        ("updatedAt", "Updated At"),
        ("archivedAt", "Archived At"),
        ("url", "URL"),
        ("slugId", "Slug ID"),
        ("color", "Color"),
        ("icon", "Icon"),
        ("organization.name", "Organization"),
        ("projects", "Projects"),
    ]

    def __init__(self, initiatives: List[Dict[str, Any]]):
        """Initialize exporter.

        Args:
            initiatives: List of initiative objects
        """
        self.initiatives = initiatives

    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from object using dot notation.

        Args:
            obj: Object to get value from
            path: Dot-separated path (e.g., "organization.name")

        Returns:
            Value at path, or None if not found
        """
        keys = path.split(".")
        value = obj

        for key in keys:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _format_value(self, value: Any) -> str:
        """Format value for export.

        Args:
            value: Value to format

        Returns:
            Formatted string value
        """
        if value is None:
            return ""

        # Handle lists (like projects)
        if isinstance(value, list):
            if not value:
                return ""
            # If list of dicts with 'name', extract names
            if all(isinstance(item, dict) and "name" in item for item in value):
                return ", ".join(item["name"] for item in value)
            # Otherwise join as strings
            return ", ".join(str(item) for item in value)

        # Handle nested dicts
        if isinstance(value, dict):
            # For nodes array, extract names
            if "nodes" in value:
                return self._format_value(value["nodes"])
            return str(value)

        return str(value)

    def _prepare_row(self, initiative: Dict[str, Any]) -> Dict[str, str]:
        """Prepare a single initiative row for export.

        Args:
            initiative: Initiative object

        Returns:
            Dictionary with formatted values
        """
        row = {}

        for field_path, display_name in self.EXPORT_FIELDS:
            # Special handling for projects (nodes array)
            if field_path == "projects":
                value = initiative.get("projects", {})
                if isinstance(value, dict) and "nodes" in value:
                    value = value["nodes"]
                else:
                    value = []
            else:
                value = self._get_nested_value(initiative, field_path)

            row[display_name] = self._format_value(value)

        return row

    def to_csv(self, output: TextIO = sys.stdout) -> None:
        """Export initiatives to CSV format.

        Args:
            output: Output stream (default: stdout)
        """
        if not self.initiatives:
            # Still write headers even if no data
            writer = csv.DictWriter(output, fieldnames=[name for _, name in self.EXPORT_FIELDS])
            writer.writeheader()
            return

        # Prepare rows
        rows = [self._prepare_row(initiative) for initiative in self.initiatives]

        # Write CSV
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    def to_json(self, output: TextIO = sys.stdout, pretty: bool = True) -> None:
        """Export initiatives to JSON format.

        Args:
            output: Output stream (default: stdout)
            pretty: Whether to pretty-print JSON (default: True)
        """
        if pretty:
            json.dump(self.initiatives, output, indent=2, default=str)
        else:
            json.dump(self.initiatives, output, default=str)

        # Add newline at end
        output.write("\n")

    def to_tsv(self, output: TextIO = sys.stdout) -> None:
        """Export initiatives to TSV (tab-separated values) format.

        Args:
            output: Output stream (default: stdout)
        """
        if not self.initiatives:
            # Still write headers even if no data
            writer = csv.DictWriter(output, fieldnames=[name for _, name in self.EXPORT_FIELDS], delimiter="\t")
            writer.writeheader()
            return

        # Prepare rows
        rows = [self._prepare_row(initiative) for initiative in self.initiatives]

        # Write TSV
        writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    def export(self, format: str = "csv", output: TextIO = sys.stdout) -> None:
        """Export initiatives in specified format.

        Args:
            format: Output format ('csv', 'json', 'tsv')
            output: Output stream (default: stdout)

        Raises:
            ValueError: If format is not supported
        """
        format = format.lower()

        if format == "csv":
            self.to_csv(output)
        elif format == "json":
            self.to_json(output)
        elif format == "tsv":
            self.to_tsv(output)
        else:
            raise ValueError(f"Unsupported format: {format}. Supported formats: csv, json, tsv")
