from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    encode_function_data,
)
from brownie import (
    GovernorContract,
    GovernanceToken,
    GovernanceTimeLock,
    Box,
    Contract,
    config,
    network,
    accounts,
    chain,
)
import scripts.constants as const
from web3 import Web3, constants


def deploy_governor():
    account = get_account()
    governance_token = (
        GovernanceToken.deploy(
            const.INITIAL_SUPPLY,
            {"from": account},
            publish_source=config["networks"][network.show_active()].get(
                "verify", False
            ),
        )
        if len(GovernanceToken) <= 0
        else GovernanceToken[-1]
    )
    governance_token.delegate(account, {"from": account})
    print(f"Checkpoints: {governance_token.numCheckpoints(account)}")

    governance_time_lock = governance_time_lock = (
        GovernanceTimeLock.deploy(
            const.MIN_DELAY,
            [],
            [],
            {"from": account},
            publish_source=config["networks"][network.show_active()].get(
                "verify", False
            ),
        )
        if len(GovernanceTimeLock) <= 0
        else GovernanceTimeLock[-1]
    )
    governor = GovernorContract.deploy(
        governance_token.address,
        governance_time_lock.address,
        const.VOTING_DELAY,
        const.VOTING_PERIOD,
        const.QUORUM_PERCENTAGE,
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )

    proposer_role = governance_time_lock.PROPOSER_ROLE()
    executor_role = governance_time_lock.EXECUTOR_ROLE()
    timelock_admin_role = governance_time_lock.TIMELOCK_ADMIN_ROLE()
    governance_time_lock.grantRole(proposer_role, governor, {"from": account})
    governance_time_lock.grantRole(
        executor_role, constants.ADDRESS_ZERO, {"from": account}
    )
    tx = governance_time_lock.revokeRole(
        timelock_admin_role, account, {"from": account}
    )
    tx.wait(1)


def deploy_box_to_be_governed():
    account = get_account()
    box = Box.deploy({"from": account})
    tx = box.transferOwnership(GovernanceTimeLock[-1], {"from": account})
    tx.wait(1)


def propose(store_value):
    account = get_account()
    encoded_function = encode_function_data(Box[-1].store, store_value)
    print(encoded_function)
    propose_tx = GovernorContract[-1].propose(
        [Box[-1].address],
        [0],
        [encoded_function],
        const.PROPOSAL_DESCRIPTION,
        {"from": account},
    )
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        move_blocks(2)
    propose_tx.wait(2)
    proposal_id = propose_tx.events["ProposalCreated"]["proposalId"]
    print(f"Proposal state {GovernorContract[-1].state(proposal_id)}")
    print(f"Proposal snapshot {GovernorContract[-1].proposalSnapshot(proposal_id)}")
    print(f"Proposal deadline {GovernorContract[-1].proposalDeadline(proposal_id)}")
    return proposal_id


def vote(proposal_id: int, vote: int):
    # 0 = Against, 1 = For, 2 = Abstain
    print(f"voting yes on {proposal_id}")
    account = get_account()
    tx = GovernorContract[-1].castVote(
        proposal_id, vote, {"from": account}
    )
    tx.wait(1)
    print(tx.events["VoteCast"])


def queue_and_execute(store_value):
    account = get_account()
    encoded_function = encode_function_data(Box[-1].store, store_value)
    description_hash = Web3.keccak(text=const.PROPOSAL_DESCRIPTION).hex()
    tx = GovernorContract[-1].queue(
        [Box[-1].address],
        [0],
        [encoded_function],
        description_hash,
        {"from": account},
    )
    tx.wait(1)

    tx = GovernorContract[-1].execute(
        [Box[-1].address],
        [0],
        [encoded_function],
        description_hash,
        {"from": account},
    )
    tx.wait(1)


def move_blocks(amount):
    for block in range(amount):
        get_account().transfer(get_account(), "0 ether")
    print(chain.height)


def main():
    deploy_governor()
    deploy_box_to_be_governed()
    proposal_id = propose(const.NEW_STORE_VALUE)
    print(f"Proposal ID {proposal_id}")
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        move_blocks(1)
    vote(proposal_id, 1)
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        move_blocks(const.VOTING_PERIOD)
    # States: {Pending, Active, Canceled, Defeated, Succeeded, Queued, Expired, Executed }
    print(f" This proposal is currently {GovernorContract[-1].state(proposal_id)}")
    queue_and_execute(const.NEW_STORE_VALUE)
    print("Proposal executed...")
    print(f"value in Box changed to {Box[-1].retrieve()}")
