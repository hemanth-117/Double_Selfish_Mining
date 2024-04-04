class Block:
    def __init__(self, block_id, prev_block_id, miner_id,length,time,balances):
        self.block_id  = block_id
        self.prev_block_id = prev_block_id
        self.miner_id = miner_id
        self.transactions = []
        self.length = length
        self.time = time
        self.balances = balances

    
