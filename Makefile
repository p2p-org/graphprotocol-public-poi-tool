all: codegen

codegen: network_client indexer_status_client ebo_client

network_client:
	poetry run ariadne-codegen --config codegen/network_subgraph/config.toml client

indexer_status_client:
	poetry run ariadne-codegen --config codegen/indexer_status/config.toml client

ebo_client:
	poetry run ariadne-codegen --config codegen/ebo/config.toml client

ARIADNE_MODULE_PATH=".venv/lib/python3.11/site-packages/ariadne_codegen"

base_client:
	cp $(ARIADNE_MODULE_PATH)/client_generators/dependencies/base_client.py graph_poitool/clients/gql/base_client.py
	cp $(ARIADNE_MODULE_PATH)/client_generators/dependencies/exceptions.py graph_poitool/clients/gql/exceptions.py

clean:
	rm -rf graph_poitools/clients/network
	rm -rf graph_poitools/clients/indexer_status
	rm -rf graph_poitools/clients/ebo
