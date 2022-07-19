from web3 import Web3

INITIAL_SUPPLY = Web3.toWei(1000, "ether")

QUORUM_PERCENTAGE = 4

VOTING_PERIOD = 5  # in blocks
VOTING_DELAY = 1  


MIN_DELAY = 1  # in seconds


PROPOSAL_DESCRIPTION = "Proposal #1: Store 1 in the Box!"
NEW_STORE_VALUE = 5