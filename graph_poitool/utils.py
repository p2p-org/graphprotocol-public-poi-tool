def configure_logging():
    pass


def status_url(indexer):
    indexer_url = indexer.url.rstrip("/")
    return f"{indexer_url}/status"


NETWORK_IDS = {
    "mainnet": "eip155:1",
    "goerli": "eip155:5",
    "gnosis": "eip155:100",
    "hardhat": "eip155:1337",
    "arbitrum-one": "eip155:42161",
    "arbitrum-goerli": "eip155:421613",
    "arbitrum-sepolia": "eip155:421614",
    "avalanche": "eip155:43114",
    "matic": "eip155:137",
    "celo": "eip155:42220",
    "optimism": "eip155:10",
    "fantom": "eip155:250",
    "sepolia": "eip155:11155111",
    "bsc": "eip155:56",
    "linea": "eip155:59144",
    "scroll": "eip155:534352",
    "base": "eip155:8453",
    "moonbeam": "eip155:1284",
    "fuse": "eip155:122",
    "blast-mainnet": "eip155:81457",
    "boba": "eip155:288",
    "boba-bnb": "eip155:56288",
    "zora": "eip155:7777777",
    "mode-mainnet": "eip155:34443",
}


def to_network_id(name):
    if name in NETWORK_IDS:
        return NETWORK_IDS[name]
    else:
        raise KeyError(f"Unknown network {name}")
