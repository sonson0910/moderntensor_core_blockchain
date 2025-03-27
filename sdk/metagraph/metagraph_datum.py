from pycardano import PlutusData
from dataclasses import dataclass

# Datum cho Miner
@dataclass
class MinerDatum(PlutusData):
    CONSTR_ID = 0
    uid: bytes
    stake: int
    performance: int
    trust_score: int
    accumulated_rewards: int
    last_evaluated: int
    history_hash: bytes
    wallet_addr_hash: bytes
    status: bytes
    block_reg_at: int

# Datum cho Validator
@dataclass
class ValidatorDatum(PlutusData):
    CONSTR_ID = 0
    uid: str
    stake: int
    performance: int
    trust_score: int
    accumulated_rewards: int
    last_evaluated: int
    history_hash: bytes
    wallet_addr_hash: bytes
    status: str
    block_reg_at: int

# Datum cho Subnet Tĩnh
@dataclass
class SubnetStaticDatum(PlutusData):
    CONSTR_ID = 0
    net_uid: int
    name: str
    owner_addr: str
    max_slot_key: int
    max_slot_validator: int
    max_slot_miner: int
    immunity_period: int
    source_code: str
    created_at: int
    description: str
    owner_signature: bytes

# Datum cho Subnet Động
@dataclass
class SubnetDynamicDatum(PlutusData):
    CONSTR_ID = 0
    net_uid: int
    weight: int
    performance: int
    blocks_until_next_epoch: int
    blocks_until_next_adjustment: int
    reg_slot: int
    reg_cost: int
    incentive: int
    consensus: int
    last_updated: int
    total_stake: int
    validator_count: int
    miner_count: int