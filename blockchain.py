import datetime
import hashlib
import json
import os

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data_str = json.dumps(self.data, sort_keys=True)
        raw = f"{self.index}{self.timestamp}{data_str}{self.previous_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

class Blockchain:
    def __init__(self, filename):
        self.filename = filename
        self.chain = []
        self.load_chain()

    def create_genesis_block(self):
        return Block(0, datetime.datetime.now().isoformat(), 
                    {"type": "Genesis", "info": "Police Portal Started"}, "0")

    def add_block(self, data):
        if not self.chain:
            self.chain.append(self.create_genesis_block())
        
        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.datetime.now().isoformat(),
            data=data,
            previous_hash=previous_block.hash
        )
        self.chain.append(new_block)
        self.save_chain()
        return new_block

    def save_chain(self):
        try:
            chain_data = []
            for block in self.chain:
                chain_data.append({
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "data": block.data,
                    "previous_hash": block.previous_hash,
                    "hash": block.hash
                })
            with open(self.filename, 'w') as f:
                json.dump(chain_data, f, indent=4)
        except Exception as e:
            print(f"Error saving blockchain: {e}")

    def load_chain(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    chain_data = json.load(f)
                
                self.chain = []
                for bd in chain_data:
                    block = Block(bd['index'], bd['timestamp'], bd['data'], bd['previous_hash'])
                    if block.hash == bd['hash']:
                        self.chain.append(block)
                    else:
                        print("Blockchain integrity compromised!")
                        self.chain = [self.create_genesis_block()]
                        break
            except Exception as e:
                print(f"Error loading blockchain: {e}")
                self.chain = [self.create_genesis_block()]
        else:
            self.chain = [self.create_genesis_block()]

    def get_chain_json(self):
        return [{
            "index": b.index,
            "timestamp": b.timestamp,
            "type": b.data.get("type"),
            "details": b.data.get("details"),
            "previous_hash": b.previous_hash,
            "hash": b.hash
        } for b in self.chain]