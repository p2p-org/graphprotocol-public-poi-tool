# Graphprotocol Public POI Tool

A command-line tool for analyzing and reporting on Proof of Indexing (POI) data across Graph Protocol indexers. This tool helps monitor subgraph deployment health, compare POI values between indexers, and identify divergence points.

## Features

- **Health Reports**: Generate comprehensive health reports for subgraph deployments across all allocated indexers
- **POI Analysis**: Compare proof-of-indexing values between indexers at specific block numbers
- **Bisection Analysis**: Efficiently find the exact block where two indexers' POI values first diverge
- **Indexer State Hash**: Generate hashes of indexer states for finding indexers sharing graph-node

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)

### Install from source

```bash
git clone https://github.com/graphprotocol/graphprotocol-public-poi-tool.git
cd graphprotocol-public-poi-tool
poetry install
```

## Configuration

The tool requires access to Graph Protocol subgraph endpoints. Configure these via environment variables or command-line options:

```bash
export POITOOL_NETWORK_SUBGRAPH_ENDPOINT="https://gateway.network.thegraph.com/api/subgraphs/id/..."
export POITOOL_EBO_SUBGRAPH_ENDPOINT="https://gateway.network.thegraph.com/api/subgraphs/id/..."
export POITOOL_GATEWAY_API_TOKEN="secret" # optional if not pointing to gateway
```

## Usage

### Health Reports

Generate a health report for a subgraph deployment:

```bash
poitool health <DEPLOYMENT_ID>
```

This command:
- Queries all indexers with allocations to the deployment
- Displays health status, latest block, and error information
- Shows results in a real-time updating table

### Proof of Indexing Reports

Generate POI reports for specific blocks:

```bash
# Use current epoch's latest valid block
poitool poi report <IPFS_HASH>

# Use specific block number
poitool poi report <IPFS_HASH> <BLOCK_NUMBER>
```

Features:
- Collects POI values from all allocated indexers
- Compares POI consistency across the network
- Identifies indexers with matching/divergent POI values

### POI Bisection

Find the exact block where two indexers' POI values diverge:

```bash
poitool poi bisect <IPFS_HASH> <LEFT_INDEXER_ID> <RIGHT_INDEXER_ID>
```

This uses binary search to efficiently locate divergence points, useful for:
- Debugging indexing discrepancies
- Identifying when indexers went out of agreement
- Root cause analysis of POI mismatches

### Indexer State Hashing

Generate a hash of an indexer's synced subgraph identifiers:

```bash
poitool indexer hash <INDEXER_ID>
```

Useful for:
- Finding indexers that are sharing graph-node

## Architecture

### Core Components

- **Network Client**: Interfaces with the Graph Network subgraph
- **EBO Client**: Interfaces with Epoch Block Oracle for valid block numbers
- **Indexer Status Client**: Communicates with individual indexer status endpoints
- **Report Service**: Generates health and POI reports across multiple indexers
- **Bisector Service**: Performs binary search to find POI divergence points

### Services

- **`ReportService`**: Orchestrates data collection from multiple indexers
- **`BisectorService`**: Implements efficient bisection algorithm for POI analysis

### Clients

- **`NetworkClient`**: Queries network subgraph for allocations, indexer info, and manifests
- **`EBOClient`**: Retrieves epoch and block validation data
- **`IndexerStatusClient`**: Queries individual indexer endpoints for status and POI data

## Command Reference

### Global Options

- `--network-subgraph-endpoint`: Graph Network subgraph endpoint
- `--ebo-subgraph-endpoint`: EBO subgraph endpoint
- `--gateway-api-token`: Graph Gateway API token

### Commands

#### `health <IPFS_HASH>`
Generate health report for a subgraph deployment.

#### `poi report <IPFS_HASH> [BLOCK_NUMBER]`
Generate POI report. Block number defaults to current epoch's latest valid block.

#### `poi bisect <IPFS_HASH> <LEFT_INDEXER_ID> <RIGHT_INDEXER_ID>`
Find first divergent block between two indexers using binary search.

#### `indexer hash <INDEXER_ID>`
Generate SHA-256 hash of indexer's synced subgraphs and their health status.

## Development

### Setup Development Environment

```bash
poetry install
```

### Code Generation

The project uses GraphQL code generation for type-safe client interactions:

```bash
# Generate client code from GraphQL schemas
make codegen
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation and code comments
