all: codegen

codegen: network_client indexer_status_client ebo_client

network_client:
	poetry run ariadne-codegen --config codegen/network_subgraph/config.toml client
	uv run ruff check --fix graph_poitool/clients/network

indexer_status_client:
	poetry run ariadne-codegen --config codegen/indexer_status/config.toml client
	uv run ruff check --fix graph_poitool/clients/indexer_status

ebo_client:
	poetry run ariadne-codegen --config codegen/ebo/config.toml client
	uv run ruff check --fix graph_poitool/clients/ebo

codegen_clean:
	rm -rf graph_poitools/clients/network
	rm -rf graph_poitools/clients/indexer_status
	rm -rf graph_poitools/clients/ebo

clean:
	rm -rf dist

build:
	uv build --wheel

publish:
	uv publish

