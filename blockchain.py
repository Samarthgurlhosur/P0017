import hashlib
import datetime
import json

class Block:
    def __init__(self, index, data, previous_hash):
        self.index = index
        self.timestamp = str(datetime.datetime.now())
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = (
            str(self.index) +
            self.timestamp +
            json.dumps(self.data, sort_keys=True) +
            self.previous_hash
        )
        return hashlib.sha256(block_string.encode()).hexdigest()
class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, "Genesis Block", "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()
        new_block = Block(len(self.chain), data, previous_block.hash)
        self.chain.append(new_block)
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Check if hash is correct
            if current.hash != current.calculate_hash():
                return False

            # Check if previous hash matches
            if current.previous_hash != previous.hash:
                return False

        return True


class GovernmentProject:
    def __init__(self, project_id, project_name, total_budget):
        self.project_id = project_id
        self.project_name = project_name
        self.total_budget = total_budget
        self.released_amount = 0

        # Define milestone percentages
        self.milestones = {
            "Milestone 1": 0.30,
            "Milestone 2": 0.40,
            "Milestone 3": 0.30
        }

        self.completed_milestones = []
    def release_funds(self, milestone_name):
        if milestone_name not in self.milestones:
            return "Invalid milestone."

        if milestone_name in self.completed_milestones:
            return "Milestone already completed."

        percentage = self.milestones[milestone_name]
        amount_to_release = self.total_budget * percentage

        if self.released_amount + amount_to_release > self.total_budget:
            return "Cannot release more than total budget."

        self.released_amount += amount_to_release
        self.completed_milestones.append(milestone_name)

        return amount_to_release
class Contractor:
    def __init__(self, contractor_id, name):
        self.contractor_id = contractor_id
        self.name = name
        self.balance = 0

    def receive_funds(self, amount):
        self.balance += amount

    def make_payment(self, recipient, amount):
        if amount > self.balance:
            return "Insufficient funds."

        self.balance -= amount
        return {
            "from": self.name,
            "to": recipient,
            "amount": amount
        }