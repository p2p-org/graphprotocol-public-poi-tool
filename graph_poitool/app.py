from dataclasses import dataclass
from functools import partial
from math import log, ceil

from graph_poitool.clients.indexer_status import Health
from graph_poitool.clients.network import NetworkClient
from graph_poitool.clients.ebo import EBOClient
from graph_poitool.utils import status_url, to_network_id

from rich.console import Console
from rich.table import Table
from rich.progress import track, Progress
from rich.live import Live


import click


@dataclass
class PoiToolsContext:
    network: NetworkClient
    ebo: EBOClient


@click.group()
@click.option("--network-subgraph-endpoint", envvar="POITOOL_NETWORK_SUBGRAPH_ENDPOINT")
@click.option("--ebo-subgraph-endpoint", envvar="POITOOL_EBO_SUBGRAPH_ENDPOINT")
@click.pass_context
def cli(ctx, network_subgraph_endpoint, ebo_subgraph_endpoint):
    network = NetworkClient(network_subgraph_endpoint)
    ebo = EBOClient(ebo_subgraph_endpoint)
    ctx.obj = PoiToolsContext(network=network, ebo=ebo)


@cli.command()
@click.argument("DEPLOYMENT_ID")
@click.pass_context
def health(ctx, deployment_id):
    table = Table(title="Status Report")
    table.add_column("Indexer ID")
    table.add_column("Indexer URL")
    table.add_column("Status")
    table.add_column("Latest Block")
    table.add_column("Deterministic Error")
    table.add_column("Error")

    allocations = ctx.obj.network.subgraph_allocations(deployment_id)
    with Live(table, refresh_per_second=4) as live:
        for a in track(allocations, description="Querying Indexing Statuses..."):
            indexer = a.indexer.client
            try:
                status = indexer.subgraph_status(deployment_id)[0]
                latest_block = str(status.latest_block.number)

                if status.health == Health.failed and status.fatal_error:
                    deterministic_error = str(status.fatal_error.deterministic)
                    error = status.fatal_error.message
                else:
                    deterministic_error = None
                    error = None

                table.add_row(
                    a.indexer.id,
                    a.indexer.url,
                    status.health,
                    latest_block,
                    deterministic_error,
                    error,
                )
            except Exception as e:
                table.add_row(
                    a.indexer.id,
                    a.indexer.url,
                    "unknown",
                    "",
                    "",
                    f"Unable to query the status endpoint: {e}",
                )


@cli.group()
def poi():
    pass


@poi.command()
@click.argument("DEPLOYMENT_ID")
@click.argument("BLOCK_NUMBER", required=False, type=int)
@click.pass_context
def report(ctx, deployment_id, block_number):
    if not block_number:
        # Get last epoch block number from EBO
        manifest = ctx.obj.network.manifest(deployment_id)
        network_id = to_network_id(manifest.network)
        epoch = ctx.obj.ebo.current_epoch(network_id)
        block_number = epoch.latest_valid_block_number.block_number

    table = Table(title=f"POI Report for {deployment_id} at block {block_number}")
    table.add_column("Indexer ID")
    table.add_column("Indexer URL")
    table.add_column("Latest Block")
    table.add_column("POI")

    allocations = ctx.obj.network.subgraph_allocations(deployment_id)
    with Live(table, refresh_per_second=4) as live:
        for a in track(allocations, description="Querying Public Proofs of Indexing..."):
            indexer = a.indexer.client
            try:
                status = indexer.subgraph_status(deployment_id)[0]
                latest_block = status.latest_block.number

                if latest_block > block_number:
                    poi_result = indexer.public_poi(deployment_id, block_number)
                    poi = poi_result[0].proof_of_indexing
                else:
                    poi = None

                table.add_row(a.indexer.id, a.indexer.url, str(latest_block), poi)
            except Exception as e:
                table.add_row(a.indexer.id, a.indexer.url, "unknown", f"Unable to get POI: {e}")


def _poi_eq(deployment_id, block_number, left, right):
    left_poi = left.public_poi(deployment_id, block_number)[0]
    right_poi = right.public_poi(deployment_id, block_number)[0]
    return left_poi.proof_of_indexing == right_poi.proof_of_indexing


@poi.command()
@click.argument("DEPLOYMENT_ID")
@click.argument("LEFT_ID")
@click.argument("RIGHT_ID")
@click.pass_context
def bisect(ctx, deployment_id, left_id, right_id):
    manifest = ctx.obj.network.manifest(deployment_id)

    left = ctx.obj.network.indexer(left_id).client
    left_status = left.subgraph_status(deployment_id)[0]

    right = ctx.obj.network.indexer(right_id).client
    right_status = right.subgraph_status(deployment_id)[0]

    poi_eq = partial(_poi_eq, deployment_id, left=left, right=right)

    lo = manifest.start_block
    hi = min(left_status.latest_block.number, right_status.latest_block.number)

    if poi_eq(hi):
        print("POI on latest block matches.")
    hi -= 1

    if not poi_eq(lo):
        print("POI Mismatch on first block of the subgraph. Possible issues on graft base?")

    with Progress() as progress:
        task = progress.add_task("Finding last matching block...", total=None)

        while lo < hi:
            mid = (lo + hi) // 2

            progress.update(
                task, description=f"Checking block {mid}. {hi - lo} blocks remaining..."
            )

            if poi_eq(mid):
                if not poi_eq(mid + 1):
                    lo = mid
                    break
                else:
                    lo = mid + 1
            else:
                hi = mid

    print(f"Last block with matching POI: {lo}")


@cli.command()
@click.argument("DEPLOYMENT_ID")
@click.argument("BLOCK_NUMBER", type=int)
@click.argument("LEFT_ID")
@click.argument("RIGHT_ID")
@click.pass_context
def analyze(ctx, deployment_id, block_number, left_id, right_id):
    left = ctx.obj.network.indexer(left_id).client
    left_status = left.subgraph_status(deployment_id)[0]

    right = ctx.obj.network.indexer(right_id).client
    right_status = right.subgraph_status(deployment_id)[0]

    # changes = left.entity_changes(deployment_id, block_number)
    # print(changes)
    # changes = right.entity_changes(deployment_id, block_number)
    # print(changes)

    network = left_status.chains[0].network
    block_hash = left.block_hash(network, block_number)
    print(block_hash)

    block_data = left.block_data(network, block_hash)
    print(block_data)

    block_data = right.block_data(network, block_hash)
    print(block_data)

    cached_calls = left.cached_ethereum_calls(network, block_hash)
    print(cached_calls)

    cached_calls = right.cached_ethereum_calls(network, block_hash)
    print(cached_calls)


if __name__ == "__main__":
    cli()
