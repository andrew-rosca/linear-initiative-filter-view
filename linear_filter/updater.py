"""View updater logic."""
from typing import List, Dict, Any, Optional
from .linear_client import LinearClient
from .config import ViewConfig
from .filter_parser import parse_filter
from .client_side_filter import ClientSideFilter


class ViewUpdater:
    """Handles updating Linear custom views with initiative filters."""

    def __init__(self, client: LinearClient):
        """Initialize updater.

        Args:
            client: Linear API client
        """
        self.client = client

    def get_filter_from_config(self, view_config: ViewConfig) -> Dict[str, Any]:
        """Get GraphQL filter from view configuration.

        Args:
            view_config: View configuration with filter or GraphQL query

        Returns:
            GraphQL InitiativeFilter object

        Note:
            For raw GraphQL queries, this extracts the filter portion.
            The full query syntax is not supported for custom view filters.
        """
        if view_config.filter:
            # Parse SQL-like filter to GraphQL
            return parse_filter(view_config.filter)
        elif view_config.graphql_query:
            # For raw GraphQL, we need to extract just the filter part
            # This is a simplified approach - user should provide the filter object directly
            raise ValueError(
                "Raw GraphQL queries are not fully supported yet. "
                "Please use the simplified filter syntax instead, or provide the filter object directly."
            )
        else:
            raise ValueError("View must have either filter or graphql_query")

    async def get_custom_view(self, view_config: ViewConfig) -> Optional[Dict[str, Any]]:
        """Get custom view by ID or name.

        Args:
            view_config: View configuration

        Returns:
            CustomView object or None if not found
        """
        if view_config.view_id:
            return await self.client.get_custom_view_by_id(view_config.view_id)
        elif view_config.title:
            return await self.client.get_custom_view_by_name(view_config.title)
        else:
            raise ValueError("View must have either view_id or title")

    async def update_view(
        self,
        view_config: ViewConfig,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Update a single view with initiatives matching the filter.

        Args:
            view_config: View configuration
            dry_run: If True, only show what would be done without making changes

        Returns:
            Dictionary with update results
        """
        # Get the custom view
        view = await self.get_custom_view(view_config)

        if not view:
            identifier = view_config.title or view_config.view_id
            raise ValueError(f"Custom view not found: {identifier}")

        # Get the filter from config
        filter_obj = self.get_filter_from_config(view_config)

        # Get current initiatives in the view
        current_initiatives_data = view.get("initiatives", {}).get("nodes", [])
        old_initiatives = {init["id"] for init in current_initiatives_data}

        # Check if we need client-side filtering
        requires_client_side = ClientSideFilter.requires_client_side_filtering(filter_obj)
        
        if requires_client_side:
            # Fetch ALL initiatives and apply filter client-side
            all_initiatives = await self.client.get_initiatives(None)
            new_initiatives_list = ClientSideFilter.apply_filter(all_initiatives, filter_obj)
        else:
            # Use Linear's native filtering
            new_initiatives_list = await self.client.get_initiatives(filter_obj)
        
        new_initiatives = {init["id"] for init in new_initiatives_list}

        # Calculate changes
        added = new_initiatives - old_initiatives
        removed = old_initiatives - new_initiatives
        unchanged = old_initiatives & new_initiatives

        # Check if initiatives changed
        initiatives_changed = old_initiatives != new_initiatives

        result = {
            "view_id": view["id"],
            "view_name": view["name"],
            "initiatives_changed": initiatives_changed,
            "filter": filter_obj,
            "dry_run": dry_run,
            "initiative_count": len(new_initiatives),
            "old_initiative_count": len(old_initiatives),
            "added_count": len(added),
            "removed_count": len(removed),
            "unchanged_count": len(unchanged),
            "client_side_filtering": requires_client_side,
        }

        # Update the view (unless dry run)
        if not dry_run:
            if initiatives_changed:
                updated_view = await self.client.update_custom_view_with_initiative_filter(
                    view["id"],
                    list(new_initiatives)
                )
                result["updated"] = True
            else:
                result["updated"] = False
                result["skipped"] = True
                result["skip_reason"] = "Initiatives unchanged"
        else:
            result["updated"] = False

        return result

    async def update_all_views(
        self,
        view_configs: List[ViewConfig],
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Update all configured views.

        Args:
            view_configs: List of view configurations
            dry_run: If True, only show what would be done without making changes

        Returns:
            List of update results for each view
        """
        results = []

        for view_config in view_configs:
            try:
                result = await self.update_view(view_config, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                # Capture errors but continue with other views
                identifier = view_config.title or view_config.view_id
                results.append({
                    "view_id": None,
                    "view_name": identifier,
                    "error": str(e),
                    "dry_run": dry_run,
                })

        return results
