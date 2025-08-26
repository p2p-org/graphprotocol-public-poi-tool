class LatestBlockMixin:
    @property
    def latest_block(self):
        if len(self.chains) > 0 and self.chains[0].latest_block:
            return self.chains[0].latest_block
        else:
            return None
