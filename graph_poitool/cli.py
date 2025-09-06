from dataclasses import dataclass
from functools import partial
import hashlib

from graph_poitool.clients.network import NetworkClient
from graph_poitool.clients.ebo import EBOClient
from graph_poitool.services.report import ReportService
from graph_poitool.services.bisect import BisectorService

from rich.console import Console
from rich.table import Table
from rich.progress import track, Progress
from rich.live import Live


import click


@dataclass
class PoiToolsContext:
    """Context object for CLI commands containing initialized clients and services.
    
    Attributes:
        network: Network subgraph client
        ebo: EBO (Epoch Block Oracle) client
        reporter: Report generation service
        bisector: POI bisection service
    """
    network: NetworkClient
    ebo: EBOClient
    reporter: ReportService
    bisector: BisectorService


@click.group()
@click.option("--network-subgraph-endpoint", envvar="POITOOL_NETWORK_SUBGRAPH_ENDPOINT")
@click.option("--ebo-subgraph-endpoint", envvar="POITOOL_EBO_SUBGRAPH_ENDPOINT")
@click.pass_context
def cli(ctx, network_subgraph_endpoint, ebo_subgraph_endpoint):
    """POI Tools CLI for subgraph deployment analysis and reporting.
    
    Initializes network and EBO clients along with reporting services.
    Endpoints can be provided via command line options or environment variables.
    """
    network = NetworkClient(network_subgraph_endpoint)
    ebo = EBOClient(ebo_subgraph_endpoint)
    reporter = ReportService(network, ebo)
    bisector = BisectorService(network)
    ctx.obj = PoiToolsContext(network=network, ebo=ebo, reporter=reporter, bisector=bisector)


def report_progress_callback(progress: Progress, task, allocation, indexer, total):
    """Progress callback for report generation.
    
    Updates the progress display with current indexer being queried.
    
    Args:
        progress: Rich Progress instance
        task: Progress task ID
        allocation: Current allocation being processed
        indexer: Current indexer being queried
        total: Total number of indexers to query
    """
    progress.update(task, description=f"Querying indexer {indexer.id}...", total=total)


@cli.command()
@click.argument("DEPLOYMENT_ID")
@click.pass_context
def health(ctx, deployment_id):
    """Generate health report for a subgraph deployment.
    
    Queries all indexers with allocations to the deployment and displays
    their health status, latest block, and any errors in a table format.
    
    Args:
        deployment_id: The subgraph deployment ID to report on
    """
    """Buiild a health report for Subgraph Deploymment."""

    table = Table(title=f"Health Report for {deployment_id}")
    table.add_column("Indexer ID")
    table.add_column("Indexer URL")
    table.add_column("Status")
    table.add_column("Latest Block")
    table.add_column("Deterministic Error")
    table.add_column("Error")

    with Live(table, refresh_per_second=4) as live:
        with Progress(transient=True) as progress:
            task = progress.add_task("Querying indexers...", total=None)
            progress_callback = partial(report_progress_callback, progress, task)

            for result in ctx.obj.reporter.report(
                deployment_id, poi=False, progress_callback=progress_callback
            ):
                # Convert types because rich refuses to display bools
                if result.error_deterministic is None:
                    error_deterministic = None
                else:
                    error_deterministic = str(result.error_deterministic)

                table.add_row(
                    result.indexer_id,
                    result.indexer_url,
                    result.health,
                    str(result.latest_block),
                    error_deterministic,
                    result.error,
                )

            progress.advance(task)


@cli.group()
def poi():
    """Commands for Proof of Indexing (POI) operations."""
    pass


@poi.command()
@click.argument("DEPLOYMENT_ID")
@click.argument("BLOCK_NUMBER", required=False, type=int)
@click.pass_context
def report(ctx, deployment_id, block_number):
    """Generate POI report for a subgraph deployment at a specific block.
    
    Collects proof-of-indexing values from all indexers with allocations
    to the deployment. If no block number is specified, uses the latest
    valid block from the current epoch.
    
    Args:
        deployment_id: The subgraph deployment ID
        block_number: Optional block number (defaults to current epoch's latest valid block)
    """
    """Build Public POI report for Subgraph Deployment.
    If block number is not specified, get POI for the first block of the current epoch.
    """

    if not block_number:
        block_number = ctx.obj.reporter.sgd_latest_valid_block_number(deployment_id)

    table = Table(title=f"POI Report for {deployment_id} at block {block_number}")
    table.add_column("Indexer ID")
    table.add_column("Indexer URL")
    table.add_column("Latest Block")
    table.add_column("Public POI")

    with Live(table, refresh_per_second=4) as live:
        with Progress(transient=True) as progress:
            task = progress.add_task("Querying indexers...", total=None)
            progress_callback = partial(report_progress_callback, progress, task)

            for result in ctx.obj.reporter.report(
                deployment_id,
                poi=True,
                poi_block_number=block_number,
                progress_callback=progress_callback,
            ):
                # Build message to keep the table readable
                if result.status == "success":
                    result_message = result.public_poi
                    latest_block_message = str(result.latest_block)
                else:
                    result_message = result.error
                    latest_block_message = "unknown"

                table.add_row(
                    result.indexer_id,
                    result.indexer_url,
                    latest_block_message,
                    result_message,
                )

                progress.advance(task)


def bisect_progress_callback(progress, task, lo, mid, hi):
    """Progress callback for bisection operation.
    
    Updates the progress display with current block being checked and
    remaining blocks in the bisection range.
    
    Args:
        progress: Rich Progress instance
        task: Progress task ID
        lo: Lower bound of bisection range
        mid: Current midpoint being checked
        hi: Upper bound of bisection range
    """
    progress.update(task, description=f"Checking block {mid}. {hi - lo} blocks remaining...")


@poi.command()
@click.argument("DEPLOYMENT_ID")
@click.argument("LEFT_ID")
@click.argument("RIGHT_ID")
@click.pass_context
def bisect(ctx, deployment_id, left_id, right_id):
    """Find the first block where two indexers' POIs diverge.
    
    Uses binary search to efficiently locate the exact block number
    where proof-of-indexing values first become different between
    two specified indexers.
    
    Args:
        deployment_id: The subgraph deployment ID
        left_id: ID of the first indexer for comparison
        right_id: ID of the second indexer for comparison
    """
    left = ctx.obj.network.indexer(left_id).client
    right = ctx.obj.network.indexer(right_id).client

    with Progress() as progress:
        task = progress.add_task("Finding last matching block...", total=None)
        progress_callback = partial(bisect_progress_callback, progress, task)
        result = ctx.obj.bisector.bisect(
            deployment_id, left, right, progress_callback=progress_callback
        )

    if result.message:
        print(result.message)
    else:
        print(f"First divergent block: {result.first_diverging_block}")


@cli.group()
def indexer():
    """Commands for indexer-specific operations."""
    pass


@indexer.command()
@click.pass_context
@click.argument("INDEXER_ID")
def hash(ctx, indexer_id):
    """Generate a hash of an indexer's synced subgraphs.
    
    Creates a SHA-256 hash based on all synced subgraphs and their
    health status for the specified indexer. Useful for comparing
    indexer states or detecting changes over time.
    
    Args:
        indexer_id: The indexer ID to generate hash for
    """
    indexer = ctx.obj.network.indexer(indexer_id).client
    synced_subgraphs = indexer.synced_subgraphs(timeout=60)

    sgds = [f"{sgd.subgraph}:{sgd.health}" for sgd in synced_subgraphs]
    sgds.sort()

    m = hashlib.sha256()
    for sgd in sgds:
        m.update(sgd.encode("utf-8"))

    print(m.hexdigest())


if __name__ == "__main__":
    cli()
