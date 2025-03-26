from pycardano import PlutusData

# Datum cho Miner
class MinerDatum(PlutusData):
    CONSTR_ID = 0
    uid: str
    stake: int
    performance: float
    trust_score: float
    accumulated_rewards: int
    last_evaluated: int
    history_hash: bytes
    wallet_addr_hash: bytes
    status: str
    block_reg_at: int

# Datum cho Validator
class ValidatorDatum(PlutusData):
    CONSTR_ID = 0
    uid: str
    stake: int
    performance: float
    trust_score: float
    accumulated_rewards: int
    last_evaluated: int
    history_hash: bytes
    wallet_addr_hash: bytes
    status: str
    block_reg_at: int

# Datum cho Subnet Tĩnh
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
class SubnetDynamicDatum(PlutusData):
    CONSTR_ID = 0
    net_uid: int
    weight: float
    performance: float
    blocks_until_next_epoch: int
    blocks_until_next_adjustment: int
    reg_slot: int
    reg_cost: int
    incentive: int
    consensus: float
    last_updated: int
    total_stake: int
    validator_count: int
    miner_count: int