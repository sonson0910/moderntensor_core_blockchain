"""
Configuration loader for ModernTensor Core
Loads and manages YAML configuration files
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration loading error"""

    pass


class BlockchainConfig(BaseModel):
    """Blockchain configuration model"""

    network: str = "testnet"
    testnet_url: str = "https://rpc.test2.btcs.network"
    mainnet_url: str = "https://rpc.test2.btcs.network"
    testnet_chain_id: int = 1115
    mainnet_chain_id: int = 1116
    contract_address: str = "0xAA6B8200495F7741B0B151B486aEB895fEE8c272"
    CORE_TOKEN_ADDRESS: str = "0xbCfb1f5E120BE57cBBcB331D8392ae63C903dBaE"
    gas_price: int = 20000000000
    gas_limit: int = 6000000
    transaction_timeout: int = 120
    required_confirmations: int = 12


class BitcoinConfig(BaseModel):
    """Bitcoin integration configuration"""

    rpc_url: str = "https://bitcoin-rpc.com"
    staking_enabled: bool = True
    min_lock_time: int = 86400
    verification_enabled: bool = True
    min_confirmations: int = 6


class HTTPConfig(BaseModel):
    """HTTP client configuration"""

    timeout: int = 30
    max_connections: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0


class SlotConfig(BaseModel):
    """Consensus slot configuration"""

    duration_minutes: float = 3.5
    task_assignment_minutes: int = 1
    task_execution_minutes: int = 1
    consensus_minutes: int = 1
    metagraph_update_seconds: int = 30


class MiniBatchConfig(BaseModel):
    """Mini-batch configuration"""

    enabled: bool = True
    size: int = 5
    wait_timeout: int = 30
    interval: int = 5


class TimeoutsConfig(BaseModel):
    """Consensus timeouts configuration"""

    score_wait: int = 180
    p2p_timeout: int = 5
    network_timeout: int = 10
    commit_delay: float = 1.5


class SelectionConfig(BaseModel):
    """Miner selection configuration"""

    miners_per_cycle: int = 5
    beta_fairness: float = 0.2
    max_time_bonus: int = 10


class TrustConfig(BaseModel):
    """Trust score configuration"""

    delta_decay: float = 0.01
    alpha_base: float = 0.1
    k_alpha: float = 1.0


class PerformanceConfig(BaseModel):
    """Performance calculation configuration"""

    max_history_length: int = 100
    theta1: float = 0.1
    theta2: float = 0.6
    theta3: float = 0.3
    penalty_threshold: float = 0.05
    penalty_k: float = 10.0
    penalty_p: float = 1.0


class WeightsConfig(BaseModel):
    """Weight calculation configuration"""

    delta_w: float = 0.05
    lambda_balance: float = 0.5
    stake_log_base: float = 2.718
    time_log_base: float = 10.0


class ValidatorsConfig(BaseModel):
    """Validator requirements configuration"""

    min_for_consensus: int = 2
    required_percentage: float = 0.6


class ConsensusConfig(BaseModel):
    """Complete consensus configuration"""

    cycle_length: int = 600
    slot_duration_minutes: float = 3.5  # Added for compatibility (1+1+1+0.5)
    task_assignment_minutes: int = 1  # Added for compatibility
    task_execution_minutes: int = 1  # Added for compatibility
    consensus_minutes: int = 1  # Added for compatibility
    metagraph_update_seconds: int = 30  # Added for compatibility
    slot: SlotConfig = Field(default_factory=SlotConfig)
    mini_batch: MiniBatchConfig = Field(default_factory=MiniBatchConfig)
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    trust: TrustConfig = Field(default_factory=TrustConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    validators: ValidatorsConfig = Field(default_factory=ValidatorsConfig)

    # Consensus parameters directly accessible (flattened from YAML)
    CONSENSUS_NUM_MINERS_TO_SELECT: int = 10
    CONSENSUS_MINIBATCH_SIZE: int = 5  # Send to 5 miners per batch
    CONSENSUS_BATCH_TIMEOUT: float = 30.0
    CONSENSUS_PARAM_BETA: float = 0.2
    CONSENSUS_PARAM_MAX_TIME_BONUS: int = 10
    max_performance_history_len: int = 100


class StakingTierConfig(BaseModel):
    """Single staking tier configuration"""

    multiplier: float
    min_core: int
    min_bitcoin: float


class StakingTiersConfig(BaseModel):
    """All staking tiers configuration"""

    base: StakingTierConfig
    boost: StakingTierConfig
    super: StakingTierConfig
    satoshi: StakingTierConfig


class StakingConfig(BaseModel):
    """Staking configuration"""

    dual_staking: Dict[str, Any] = Field(default_factory=dict)
    tiers: Optional[StakingTiersConfig] = None
    minimums: Dict[str, int] = Field(default_factory=dict)
    bitcoin: Dict[str, Any] = Field(default_factory=dict)
    rewards: Dict[str, Any] = Field(default_factory=dict)
    slashing: Dict[str, Any] = Field(default_factory=dict)
    unstaking: Dict[str, Any] = Field(default_factory=dict)


class ModernTensorConfig:
    """Main configuration manager"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent

        self.config_dir = Path(config_dir)
        self._blockchain: Optional[BlockchainConfig] = None
        self._consensus: Optional[ConsensusConfig] = None
        self._staking: Optional[StakingConfig] = None

        # Load all configs
        self._load_configs()

    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        file_path = self.config_dir / filename

        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded config: {filename}")
                return config or {}
        except Exception as e:
            logger.error(f"Error loading config {filename}: {e}")
            raise ConfigError(f"Failed to load {filename}: {e}")

    def _load_configs(self):
        """Load all configuration files"""
        try:
            # Load blockchain config
            blockchain_data = self._load_yaml_file("blockchain.yaml")
            if "blockchain" in blockchain_data:
                self._blockchain = BlockchainConfig(**blockchain_data["blockchain"])
            else:
                self._blockchain = BlockchainConfig()

            # Load consensus config
            consensus_data = self._load_yaml_file("consensus.yaml")
            if "consensus" in consensus_data:
                consensus_dict = consensus_data["consensus"]

                # Handle nested configs
                if "slot" in consensus_dict:
                    consensus_dict["slot"] = SlotConfig(**consensus_dict["slot"])
                if "mini_batch" in consensus_dict:
                    consensus_dict["mini_batch"] = MiniBatchConfig(
                        **consensus_dict["mini_batch"]
                    )
                if "timeouts" in consensus_dict:
                    consensus_dict["timeouts"] = TimeoutsConfig(
                        **consensus_dict["timeouts"]
                    )
                if "selection" in consensus_dict:
                    consensus_dict["selection"] = SelectionConfig(
                        **consensus_dict["selection"]
                    )
                if "trust" in consensus_dict:
                    consensus_dict["trust"] = TrustConfig(**consensus_dict["trust"])
                if "performance" in consensus_dict:
                    consensus_dict["performance"] = PerformanceConfig(
                        **consensus_dict["performance"]
                    )
                if "weights" in consensus_dict:
                    consensus_dict["weights"] = WeightsConfig(
                        **consensus_dict["weights"]
                    )
                if "validators" in consensus_dict:
                    consensus_dict["validators"] = ValidatorsConfig(
                        **consensus_dict["validators"]
                    )

                # Extract flattened consensus parameters and use them as defaults
                flattened_params = {}
                for key in [
                    "CONSENSUS_NUM_MINERS_TO_SELECT",
                    "CONSENSUS_MINIBATCH_SIZE",
                    "CONSENSUS_BATCH_TIMEOUT",
                ]:
                    if key in consensus_dict:
                        flattened_params[key] = consensus_dict[key]

                # Also extract from nested performance config if available
                if "performance" in consensus_dict and isinstance(
                    consensus_dict["performance"], dict
                ):
                    if "max_history_length" in consensus_dict["performance"]:
                        flattened_params["max_performance_history_len"] = (
                            consensus_dict["performance"]["max_history_length"]
                        )

                # Merge with defaults in the config
                consensus_dict.update(flattened_params)

                self._consensus = ConsensusConfig(**consensus_dict)
            else:
                self._consensus = ConsensusConfig()

            # Load staking config
            staking_data = self._load_yaml_file("staking.yaml")
            if "staking" in staking_data:
                staking_dict = staking_data["staking"]

                # Handle tiers specially
                if "tiers" in staking_dict:
                    tiers_data = staking_dict["tiers"]
                    staking_dict["tiers"] = StakingTiersConfig(
                        base=StakingTierConfig(**tiers_data["base"]),
                        boost=StakingTierConfig(**tiers_data["boost"]),
                        super=StakingTierConfig(**tiers_data["super"]),
                        satoshi=StakingTierConfig(**tiers_data["satoshi"]),
                    )

                self._staking = StakingConfig(**staking_dict)
            else:
                self._staking = StakingConfig()

            logger.info("All configurations loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            raise ConfigError(f"Configuration loading failed: {e}")

    @property
    def blockchain(self) -> BlockchainConfig:
        """Get blockchain configuration"""
        if self._blockchain is None:
            self._blockchain = BlockchainConfig()
        return self._blockchain

    @property
    def consensus(self) -> ConsensusConfig:
        """Get consensus configuration"""
        if self._consensus is None:
            self._consensus = ConsensusConfig()
        return self._consensus

    @property
    def staking(self) -> StakingConfig:
        """Get staking configuration"""
        if self._staking is None:
            self._staking = StakingConfig()
        return self._staking

    def get_node_url(self) -> str:
        """Get the appropriate node URL based on network"""
        if self.blockchain.network.lower() == "mainnet":
            return self.blockchain.mainnet_url
        else:
            return self.blockchain.testnet_url

    def get_chain_id(self) -> int:
        """Get the appropriate chain ID based on network"""
        if self.blockchain.network.lower() == "mainnet":
            return self.blockchain.mainnet_chain_id
        else:
            return self.blockchain.testnet_chain_id

    def get_staking_tier_config(self, tier_name: str) -> Optional[StakingTierConfig]:
        """Get configuration for specific staking tier"""
        if not self.staking.tiers:
            return None

        tier_map = {
            "base": self.staking.tiers.base,
            "boost": self.staking.tiers.boost,
            "super": self.staking.tiers.super,
            "satoshi": self.staking.tiers.satoshi,
        }

        return tier_map.get(tier_name.lower())

    def validate_config(self) -> bool:
        """Validate all configurations"""
        try:
            # Check that theta parameters sum to 1.0
            theta_sum = (
                self.consensus.performance.theta1
                + self.consensus.performance.theta2
                + self.consensus.performance.theta3
            )

            if abs(theta_sum - 1.0) > 1e-6:
                logger.warning(f"Theta parameters sum to {theta_sum}, not 1.0")

            # Check minimum validators
            if self.consensus.validators.min_for_consensus < 1:
                logger.error("min_for_consensus must be at least 1")
                return False

            # Check staking tiers are ordered correctly
            if self.staking.tiers:
                tiers = [
                    self.staking.tiers.base.min_core,
                    self.staking.tiers.boost.min_core,
                    self.staking.tiers.super.min_core,
                    self.staking.tiers.satoshi.min_core,
                ]

                if tiers != sorted(tiers):
                    logger.error("Staking tier minimums are not in ascending order")
                    return False

            logger.info("Configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def reload(self):
        """Reload all configurations"""
        logger.info("Reloading configurations...")
        self._load_configs()


# Global instance
_config_instance: Optional[ModernTensorConfig] = None


def get_config(config_dir: Optional[str] = None) -> ModernTensorConfig:
    """Get the global configuration instance"""
    global _config_instance

    if _config_instance is None:
        _config_instance = ModernTensorConfig(config_dir)

    return _config_instance


def reload_config():
    """Reload the global configuration"""
    global _config_instance

    if _config_instance is not None:
        _config_instance.reload()
    else:
        _config_instance = ModernTensorConfig()


# Convenience exports
def get_blockchain_config() -> BlockchainConfig:
    """Get blockchain configuration"""
    return get_config().blockchain


def get_consensus_config() -> ConsensusConfig:
    """Get consensus configuration"""
    return get_config().consensus


def get_staking_config() -> StakingConfig:
    """Get staking configuration"""
    return get_config().staking
