from dataclasses import dataclass
from functools import partial
from typing import Optional, Callable, Literal

from graph_poitool.clients.network import NetworkClient, Manifest
from graph_poitool.clients.indexer_status import IndexerStatusClient
from graph_poitool.services.bisect.exceptions import (
    ManifestNotFoundError,
    SyncStatusNotFoundError,
    InvalidManifestError,
)


@dataclass
class BisectorResult:
    """Result of bisection operation for finding POI divergence.

    Attributes:
        status: Whether POIs match or mismatch between indexers
        first_diverging_block: Block number where POIs first diverge
        message: Optional descriptive message about the result
    """

    status: Literal["poi_match", "poi_mismatch"]
    first_diverging_block: int
    message: Optional[str] = None


class BisectorService:
    """Service for bisecting subgraph deployments to find POI divergence points.

    Uses binary search to efficiently find the first block where two indexers'
    proof-of-indexing values diverge for a given subgraph deployment.
    """

    def __init__(self, network_client: NetworkClient) -> None:
        self.network = network_client

    def sgd_manifest(self, deployment_id: str) -> Manifest:
        """Get manifest for a subgraph deployment.

        Args:
            deployment_id: The subgraph deployment ID

        Returns:
            Manifest object containing deployment metadata
            
        Raises:
            ManifestNotFoundError: If no manifest is returned from the client
        """
        manifest = self.network.manifest(deployment_id)
        if manifest is None:
            raise ManifestNotFoundError(f"No manifest found for deployment ID: {deployment_id}")
        return manifest

    def sgd_start_block(self, deployment_id: str) -> int:
        """Get starting block number for a subgraph deployment.

        Args:
            deployment_id: The subgraph deployment ID

        Returns:
            Starting block number from the manifest
        """
        manifest = self.sgd_manifest(deployment_id)
        if manifest.start_block is None:
            raise InvalidManifestError(f"Start block missing in manifest for {deployment_id}")
        return manifest.start_block

    def sgd_common_latest_block(self, deployment_id, left, right) -> int:
        """Find the common latest block between two indexers.

        Args:
            deployment_id: The subgraph deployment ID
            left: Left indexer client
            right: Right indexer client

        Returns:
            Minimum latest block number between the two indexers
        """
        left_status = self.sync_status(deployment_id, left)
        right_status = self.sync_status(deployment_id, right)
        return min(left_status.latest_block_number, right_status.latest_block_number)

    def sync_status(self, deployment_id: str, client):
        """Get sync status for a deployment from an indexer client.

        Args:
            deployment_id: The subgraph deployment ID
            client: Indexer status client

        Returns:
            Sync status object with latest block and other metadata
            
        Raises:
            SyncStatusNotFoundError: If no sync status is returned from the client
        """
        status_list = client.subgraph_status(deployment_id)
        if not status_list or status_list[0] is None:
            raise SyncStatusNotFoundError(f"No sync status found for deployment ID: {deployment_id}")
        return status_list[0]

    @staticmethod
    def poi_eq(deployment_id, block_number, left, right) -> bool:
        """Check if proof-of-indexing values match between two indexers.

        Args:
            deployment_id: The subgraph deployment ID
            block_number: Block number to check POI for
            left: Left indexer client
            right: Right indexer client

        Returns:
            True if POI values match, False otherwise
        """
        left_poi = left.public_poi(deployment_id, block_number)[0]
        right_poi = right.public_poi(deployment_id, block_number)[0]
        return left_poi.proof_of_indexing == right_poi.proof_of_indexing

    def bisect(
        self,
        deployment_id: str,
        left: IndexerStatusClient,
        right: IndexerStatusClient,
        progress_callback: Optional[Callable] = None,
    ):
        """Perform binary search to find first block where POIs diverge.

        Uses bisection algorithm to efficiently find the exact block number
        where two indexers' proof-of-indexing values first become different.

        Args:
            deployment_id: The subgraph deployment ID to bisect
            left: Left indexer client for comparison
            right: Right indexer client for comparison
            progress_callback: Optional callback for progress updates

        Returns:
            BisectorResult with status and first diverging block number
        """
        poi_eq = partial(self.poi_eq, deployment_id, left=left, right=right)
        lo = self.sgd_start_block(deployment_id)
        hi = self.sgd_common_latest_block(deployment_id, left, right)

        if poi_eq(hi):
            return BisectorResult("poi_match", -1, "POI matches on latest block.")
        hi -= 1

        if not poi_eq(lo):
            return BisectorResult("poi_mismatch", lo - 1, "POI mismatch on first block.")

        while lo < hi:
            mid = (lo + hi) // 2

            if progress_callback:
                progress_callback(lo, mid, hi)

            if poi_eq(mid):
                lo = mid + 1
                if not poi_eq(mid + 1):
                    break
            else:
                hi = mid

        return BisectorResult("poi_mismatch", lo)
