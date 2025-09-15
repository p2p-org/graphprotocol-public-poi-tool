from dataclasses import dataclass
from typing import Literal, Optional, Callable
from graph_poitool.clients.gql import GraphQLClientError
from graph_poitool.clients.network import NetworkClient
from graph_poitool.clients.ebo import EBOClient
from graph_poitool.services.report.exceptions import (
    ReportServiceEBORequiredError,
)
from graph_poitool.utils import to_network_id


@dataclass
class ReportResult:
    """Report result containing indexer status and metadata.

    Attributes:
        indexer_id: Unique identifier for the indexer
        indexer_url: HTTP endpoint URL for the indexer
        status: Success or failure status of the report query
        health: Health status of the subgraph indexing
        latest_block: Most recent block number indexed (optional)
        error: Error message if any occurred (optional)
        error_deterministic: Whether the error is deterministic (optional)
        public_poi: Public proof of indexing hash (optional)
    """

    indexer_id: str
    indexer_url: str
    status: Literal["success", "failure"]
    health: Literal["healthy", "unhealthy", "failed", "unknown"]
    latest_block: Optional[int] = None
    error: Optional[str] = None
    error_deterministic: Optional[bool] = None
    public_poi: Optional[str] = None


class ReportService:
    """Service for generating reports on subgraph deployment status across indexers.

    This service queries multiple indexers to collect status information about
    a specific subgraph deployment, including health status, latest blocks,
    and proof-of-indexing data.
    """

    def __init__(self, network_client: NetworkClient, ebo_client: EBOClient) -> None:
        self.network = network_client
        self.ebo = ebo_client

    def sgd_allocations(self, deployment_id: str):
        """Get allocations for a subgraph deployment.

        Args:
            deployment_id: The subgraph deployment ID

        Returns:
            List of allocations for the deployment
        """
        return self.network.subgraph_allocations(deployment_id)

    def sgd_latest_valid_block_number(self, deployment_id: str) -> int:
        """Get the latest valid block number for a subgraph deployment.

        Uses the EBO client to determine the latest valid block number
        for the network where the subgraph is deployed.

        Args:
            deployment_id: The subgraph deployment ID

        Returns:
            Latest valid block number

        Raises:
            ReportServiceEBORequiredError: If EBO client is not available
        """
        if not self.ebo:
            raise ReportServiceEBORequiredError()
        manifest = self.network.manifest(deployment_id)
        network_id = to_network_id(manifest.network)
        epoch = self.ebo.current_epoch(network_id)
        block_number = epoch.latest_valid_block_number.block_number
        return block_number

    def report(
        self,
        deployment_id: str,
        poi: bool = False,
        poi_block_number: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ):
        """Generate a report for a subgraph deployment across all allocated indexers.

        Queries each indexer that has allocated stake to the deployment and
        collects status information including health, latest blocks, errors,
        and optionally proof-of-indexing data.

        Args:
            deployment_id: The subgraph deployment ID to report on
            poi: Whether to collect proof-of-indexing data
            poi_block_number: Specific block number for POI (defaults to latest valid)
            progress_callback: Optional callback function for progress updates

        Yields:
            ReportResult: Status report for each indexer
        """
        allocations = self.sgd_allocations(deployment_id)

        if poi and not poi_block_number:
            poi_block_number = self.sgd_latest_valid_block_number(deployment_id)

        for al in allocations:
            indexer_id = al.indexer.id
            indexer_url = al.indexer.url

            if progress_callback:
                progress_callback(al, al.indexer, total=len(allocations))

            if not indexer_url:
                yield ReportResult(
                    indexer_id,
                    "",
                    status="failure",
                    health="unknown",
                    error="Indexer has no URL",
                )
                continue

            client = al.indexer.client
            try:
                status = client.subgraph_status(deployment_id)[0]

                if (
                    poi
                    and status.latest_block_number
                    and status.latest_block_number > poi_block_number
                ):
                    public_poi_resp = client.public_poi(deployment_id, poi_block_number)[0]
                    public_poi = public_poi_resp.proof_of_indexing
                else:
                    public_poi = None

                yield ReportResult(
                    indexer_id,
                    indexer_url,
                    status="success",
                    health=status.health,
                    latest_block=status.latest_block_number,
                    error=status.fatal_error_message,
                    error_deterministic=status.fatal_error_deterministic,
                    public_poi=public_poi,
                )
            except GraphQLClientError as e:
                yield ReportResult(
                    indexer_id,
                    indexer_url,
                    status="failure",
                    health="unknown",
                    error=f"Unable to get status: {e}",
                )
