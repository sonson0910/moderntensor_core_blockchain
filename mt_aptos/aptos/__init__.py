"""
ModernTensor Aptos Integration Package.

This package provides integration with Aptos blockchain for ModernTensor.
"""

from .datatypes import (
    MinerInfo,
    ValidatorInfo,
    SubnetInfo,
    TaskAssignment,
    MinerResult,
    ValidatorScore,
    ScoreSubmissionPayload,
    MinerConsensusResult,
    CycleConsensusResults,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    STATUS_JAILED,
)

from .contract_client import ModernTensorClient
from .metagraph import (
    update_miner,
    update_validator,
    register_miner,
    register_validator,
    get_all_miners,
    get_all_validators,
)

from .module_manager import (
    get_module_bytecode,
    get_script_bytecode,
    list_available_modules,
    list_available_scripts,
    get_source_code,
    get_script_source,
)

from .service import (
    # Staking service functions
    stake_tokens,
    unstake_tokens,
    claim_rewards,
    get_staking_info,
    
    # Transaction service functions
    send_coin,
    send_token,
    submit_transaction,
    get_transaction_details,
    get_account_transactions,
)

from .contract_service import (
    execute_entry_function,
    get_module_resources,
    get_resource_by_type,
    publish_module,
)

__all__ = [
    # Datatypes
    "MinerInfo",
    "ValidatorInfo",
    "SubnetInfo",
    "TaskAssignment",
    "MinerResult",
    "ValidatorScore",
    "ScoreSubmissionPayload",
    "MinerConsensusResult",
    "CycleConsensusResults",
    "STATUS_ACTIVE",
    "STATUS_INACTIVE",
    "STATUS_JAILED",
    
    # Contract client
    "ModernTensorClient",
    
    # Metagraph functions
    "update_miner",
    "update_validator",
    "register_miner",
    "register_validator",
    "get_all_miners",
    "get_all_validators",
    
    # Module manager functions
    "get_module_bytecode",
    "get_script_bytecode",
    "list_available_modules",
    "list_available_scripts",
    "get_source_code",
    "get_script_source",
    
    # Service functions
    "stake_tokens",
    "unstake_tokens",
    "claim_rewards",
    "get_staking_info",
    "send_coin",
    "send_token",
    "submit_transaction",
    "get_transaction_details",
    "get_account_transactions",
    
    # Contract service functions
    "execute_entry_function",
    "get_module_resources",
    "get_resource_by_type",
    "publish_module",
] 