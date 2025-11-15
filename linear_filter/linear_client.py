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

    async def query_initiatives(self, graphql_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query initiatives using GraphQL filter.

        Args:
            graphql_filter: GraphQL filter object for initiatives query

        Returns:
            List of initiative objects with id, title, etc.
        """
        query = gql("""
            query GetInitiatives($filter: InitiativeFilter) {
                initiatives(filter: $filter) {
                    nodes {
                        id
                        name
                        status
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query, variable_values={"filter": graphql_filter})
            return result["initiatives"]["nodes"]

    async def query_initiatives_raw(self, raw_query: str) -> List[Dict[str, Any]]:
        """Execute a raw GraphQL query for initiatives.

        Args:
            raw_query: Raw GraphQL query string

        Returns:
            List of initiative objects
        """
        query = gql(raw_query)

        async with self.client as session:
            result = await session.execute(query)
            # Try to extract initiatives from various possible response structures
            if "initiatives" in result:
                return result["initiatives"].get("nodes", [])
            return []

    async def get_roadmap_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Get roadmap view by title.

        Args:
            title: Roadmap view title

        Returns:
            Roadmap object or None if not found
        """
        query = gql("""
            query GetRoadmaps {
                roadmaps {
                    nodes {
                        id
                        name
                        initiativeIds
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query)
            roadmaps = result["roadmaps"]["nodes"]

            for roadmap in roadmaps:
                if roadmap["name"] == title:
                    return roadmap

            return None

    async def get_roadmap_by_id(self, roadmap_id: str) -> Optional[Dict[str, Any]]:
        """Get roadmap view by ID.

        Args:
            roadmap_id: Roadmap view ID

        Returns:
            Roadmap object or None if not found
        """
        query = gql("""
            query GetRoadmap($id: String!) {
                roadmap(id: $id) {
                    id
                    name
                    initiativeIds
                }
            }
        """)

        async with self.client as session:
            try:
                result = await session.execute(query, variable_values={"id": roadmap_id})
                return result.get("roadmap")
            except Exception:
                return None

    async def update_roadmap(self, roadmap_id: str, initiative_ids: List[str]) -> Dict[str, Any]:
        """Update roadmap view with new initiative IDs.

        Args:
            roadmap_id: Roadmap view ID
            initiative_ids: List of initiative IDs to set in the view

        Returns:
            Updated roadmap object
        """
        mutation = gql("""
            mutation UpdateRoadmap($id: String!, $input: RoadmapUpdateInput!) {
                roadmapUpdate(id: $id, input: $input) {
                    success
                    roadmap {
                        id
                        name
                        initiativeIds
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                mutation,
                variable_values={
                    "id": roadmap_id,
                    "input": {"initiativeIds": initiative_ids}
                }
            )

            if not result["roadmapUpdate"]["success"]:
                raise Exception("Failed to update roadmap")

            return result["roadmapUpdate"]["roadmap"]
