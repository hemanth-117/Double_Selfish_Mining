from peer import *


class transaction:
    def __init__(self, transaction_id, idx, idy, amount, size):
        self.transaction_id = transaction_id
        self.idx = idx
        self.idy = idy
        self.amount = amount
        self.size = size


