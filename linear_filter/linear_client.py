"""Linear GraphQL API client."""
import os
from typing import List, Dict, Any, Optional
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


class LinearClient:
    """Client for interacting with Linear's GraphQL API."""

    LINEAR_API_URL = "https://api.linear.app/graphql"

    def __init__(self, api_token: Optional[str] = None):
        """Initialize Linear client.

        Args:
            api_token: Linear API token. If not provided, will use LINEAR_API_TOKEN env var.
        """
        self.api_token = api_token or os.environ.get("LINEAR_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Linear API token not provided. Set LINEAR_API_TOKEN environment "
                "variable or provide api_token in config."
            )

        # Setup GraphQL client
        transport = AIOHTTPTransport(
            url=self.LINEAR_API_URL,
            headers={"Authorization": self.api_token}
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    async def get_custom_view_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get custom view by name.

        Args:
            name: Custom view name

        Returns:
            CustomView object or None if not found
        """
        # First, get the view metadata
        query = gql("""
            query GetCustomViews {
                customViews {
                    nodes {
                        id
                        name
                        initiativeFilterData
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query)
            views = result["customViews"]["nodes"]

            for view in views:
                if view["name"] == name:
                    # Fetch all initiatives with pagination
                    view["initiatives"] = await self._get_view_initiatives(session, view["id"])
                    return view

            return None
    
    async def _get_view_initiatives(self, session, view_id: str) -> Dict[str, Any]:
        """Get all initiatives for a view with pagination.
        
        Args:
            session: Active GraphQL session
            view_id: Custom view ID
            
        Returns:
            Dictionary with 'nodes' key containing list of initiative IDs
        """
        query = gql("""
            query GetViewInitiatives($id: String!, $after: String) {
                customView(id: $id) {
                    initiatives(first: 100, after: $after) {
                        nodes {
                            id
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """)
        
        all_initiatives = []
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            variables = {"id": view_id}
            if after_cursor:
                variables["after"] = after_cursor
            
            result = await session.execute(query, variable_values=variables)
            
            if not result.get("customView"):
                break
                
            initiatives_data = result["customView"]["initiatives"]
            all_initiatives.extend(initiatives_data["nodes"])
            
            page_info = initiatives_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            after_cursor = page_info["endCursor"]
        
        return {"nodes": all_initiatives}

    async def get_custom_view_by_id(self, view_id: str) -> Optional[Dict[str, Any]]:
        """Get custom view by ID.

        Args:
            view_id: Custom view ID

        Returns:
            CustomView object or None if not found
        """
        query = gql("""
            query GetCustomView($id: String!) {
                customView(id: $id) {
                    id
                    name
                    initiativeFilterData
                }
            }
        """)

        async with self.client as session:
            try:
                result = await session.execute(query, variable_values={"id": view_id})
                view = result.get("customView")
                if view:
                    # Fetch all initiatives with pagination
                    view["initiatives"] = await self._get_view_initiatives(session, view["id"])
                return view
            except Exception:
                return None

    async def update_custom_view_with_initiative_filter(self, view_id: str, initiative_ids: List[str]) -> Dict[str, Any]:
        """Update custom view with a filter that matches specific initiative IDs.
        
        Since Linear doesn't support setting initiatives directly, we create an ID-based filter.
        This allows us to support arbitrary client-side filtering (like by description keywords)
        that Linear's native filters don't support.

        Args:
            view_id: Custom view ID
            initiative_ids: List of initiative IDs to display in the view

        Returns:
            Updated custom view object
        """
        mutation = gql("""
            mutation UpdateCustomView($id: String!, $input: CustomViewUpdateInput!) {
                customViewUpdate(id: $id, input: $input) {
                    success
                    customView {
                        id
                        name
                        initiativeFilterData
                        initiatives {
                            nodes {
                                id
                            }
                        }
                    }
                }
            }
        """)

        # Create a filter that matches these specific IDs using the 'in' operator
        # If no IDs, create an impossible filter to show empty view
        if initiative_ids:
            id_filter = {"id": {"in": initiative_ids}}
        else:
            # Empty filter - this will show no initiatives
            id_filter = {"id": {"in": []}}

        async with self.client as session:
            result = await session.execute(
                mutation,
                variable_values={
                    "id": view_id,
                    "input": {"initiativeFilterData": id_filter}
                }
            )

            if not result["customViewUpdate"]["success"]:
                raise Exception("Failed to update custom view")

            return result["customViewUpdate"]["customView"]

    async def get_initiatives(self, initiative_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get initiatives with optional filter, handling pagination.

        Args:
            initiative_filter: Optional InitiativeFilter object to filter initiatives

        Returns:
            List of initiative objects with all fields
        """
        query = gql("""
            query GetInitiatives($filter: InitiativeFilter, $after: String) {
                initiatives(filter: $filter, first: 100, after: $after) {
                    nodes {
                        id
                        name
                        description
                        content
                        status
                        sortOrder
                        startedAt
                        targetDate
                        completedAt
                        createdAt
                        updatedAt
                        archivedAt
                        url
                        slugId
                        color
                        icon
                        organization {
                            id
                            name
                        }
                        projects {
                            nodes {
                                id
                                name
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        """)

        all_initiatives = []
        has_next_page = True
        after_cursor = None

        async with self.client as session:
            while has_next_page:
                variables = {}
                if initiative_filter:
                    variables["filter"] = initiative_filter
                if after_cursor:
                    variables["after"] = after_cursor

                result = await session.execute(query, variable_values=variables if variables else None)
                
                initiatives_data = result["initiatives"]
                all_initiatives.extend(initiatives_data["nodes"])
                
                page_info = initiatives_data["pageInfo"]
                has_next_page = page_info["hasNextPage"]
                after_cursor = page_info["endCursor"]

        return all_initiatives
