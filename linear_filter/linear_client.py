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
                    return view

            return None

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
                return result.get("customView")
            except Exception:
                return None

    async def update_custom_view(self, view_id: str, initiative_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Update custom view with initiative filter.

        Args:
            view_id: Custom view ID
            initiative_filter: InitiativeFilter object to set on the view

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
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                mutation,
                variable_values={
                    "id": view_id,
                    "input": {"initiativeFilterData": initiative_filter}
                }
            )

            if not result["customViewUpdate"]["success"]:
                raise Exception("Failed to update custom view")

            return result["customViewUpdate"]["customView"]
