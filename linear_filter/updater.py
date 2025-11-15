"""View updater logic."""
from typing import List, Dict, Any, Optional
from .linear_client import LinearClient
from .config import ViewConfig
from .filter_parser import parse_filter


class ViewUpdater:
    """Handles updating Linear roadmap views with filtered initiatives."""

    def __init__(self, client: LinearClient):
        """Initialize updater.

        Args:
            client: Linear API client
        """
        self.client = client

    async def get_filtered_initiatives(self, view_config: ViewConfig) -> List[Dict[str, Any]]:
        """Get initiatives matching the view's filter.

        Args:
            view_config: View configuration with filter or GraphQL query

        Returns:
            List of matching initiatives
        """
        if view_config.graphql_query:
            # Use raw GraphQL query
            initiatives = await self.client.query_initiatives_raw(view_config.graphql_query)
        elif view_config.filter:
            # Parse SQL-like filter to GraphQL
            graphql_filter = parse_filter(view_config.filter)
            initiatives = await self.client.query_initiatives(graphql_filter)
        else:
            raise ValueError("View must have either filter or graphql_query")

        return initiatives

    async def get_roadmap(self, view_config: ViewConfig) -> Optional[Dict[str, Any]]:
        """Get roadmap view by ID or title.

        Args:
            view_config: View configuration

        Returns:
            Roadmap object or None if not found
        """
        if view_config.view_id:
            return await self.client.get_roadmap_by_id(view_config.view_id)
        elif view_config.title:
            return await self.client.get_roadmap_by_title(view_config.title)
        else:
            raise ValueError("View must have either view_id or title")

    async def update_view(
        self,
        view_config: ViewConfig,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Update a single view with filtered initiatives.

        Args:
            view_config: View configuration
            dry_run: If True, only show what would be done without making changes

        Returns:
            Dictionary with update results and statistics
        """
        # Get the roadmap
        roadmap = await self.get_roadmap(view_config)

        if not roadmap:
            identifier = view_config.title or view_config.view_id
            raise ValueError(f"Roadmap not found: {identifier}")

        # Get filtered initiatives
        initiatives = await self.get_filtered_initiatives(view_config)

        # Extract initiative IDs
        initiative_ids = [initiative["id"] for initiative in initiatives]

        # Get current initiative IDs
        current_ids = set(roadmap.get("initiativeIds", []))
        new_ids = set(initiative_ids)

        # Calculate changes
        added = new_ids - current_ids
        removed = current_ids - new_ids

        result = {
            "roadmap_id": roadmap["id"],
            "roadmap_name": roadmap["name"],
            "total_initiatives": len(initiative_ids),
            "added": len(added),
            "removed": len(removed),
            "unchanged": len(current_ids & new_ids),
            "initiative_ids": initiative_ids,
            "dry_run": dry_run,
        }

        # Update the view (unless dry run)
        if not dry_run:
            if len(initiative_ids) == 0:
                print(f"WARNING: Filter returned 0 initiatives for view '{roadmap['name']}'")
                print(f"  Current view has {len(current_ids)} initiatives")
                print(f"  Skipping update to avoid clearing the view")
                result["skipped"] = True
            else:
                updated_roadmap = await self.client.update_roadmap(
                    roadmap["id"],
                    initiative_ids
                )
                result["updated"] = True
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
                    "roadmap_id": None,
                    "roadmap_name": identifier,
                    "error": str(e),
                    "dry_run": dry_run,
                })

        return results
