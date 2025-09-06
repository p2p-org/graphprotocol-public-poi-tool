from typing import Optional
from graph_poitool.clients.indexer_status import IndexerStatusClient


class IndexerMixin:
    __client: Optional[IndexerStatusClient] = None

    @property
    def status_url(self):
        if not self.url:
            return None
        return f"{self.url.rstrip('/')}/status"

    @property
    def client(self):
        if not self.__client:
            self.__client = IndexerStatusClient(self.status_url)
        return self.__client
