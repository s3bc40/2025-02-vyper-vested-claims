import json

def load_merkle_proofs() -> dict:
    with open("merkle_proofs.json", 'r') as file:
        return json.load(file)