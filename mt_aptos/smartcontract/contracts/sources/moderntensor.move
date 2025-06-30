module full_moderntensor::moderntensor_hybrid {
    use std::string::{Self, String};
    use std::signer;
    use aptos_framework::coin;
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_framework::primary_fungible_store;
    use aptos_framework::fungible_asset::{Self, Metadata};
    use aptos_framework::object::{Self, Object};
    use aptos_framework::timestamp;

    /// Errors
    const E_NOT_ENOUGH_BALANCE: u64 = 1;
    const E_ALREADY_REGISTERED: u64 = 2;
    const E_NOT_REGISTERED: u64 = 3;
    
    /// APT Fungible Asset metadata object address
    const APT_METADATA_ADDRESS: address = @0xa;
    
    /// Get APT fungible asset metadata
    fun get_apt_metadata(): Object<Metadata> {
        object::address_to_object<Metadata>(APT_METADATA_ADDRESS)
    }
    
    /// Check balance - supports both Coin and Fungible Asset
    fun check_apt_balance(account_addr: address): u64 {
        // Try Coin first
        if (coin::is_account_registered<AptosCoin>(account_addr)) {
            coin::balance<AptosCoin>(account_addr)
        } else {
            // Try Fungible Asset
            let apt_metadata = get_apt_metadata();
            if (primary_fungible_store::is_balance_at_least(account_addr, apt_metadata, 0)) {
                (primary_fungible_store::balance(account_addr, apt_metadata) as u64)
            } else {
                0
            }
        }
    }
    


    /// Full Validator info with all ModernTensor fields
    struct ValidatorInfo has key, copy, drop {
        uid: String,                        // Unique identifier
        subnet_uid: u64,                    // Subnet ID
        stake: u64,                         // Stake amount in octas
        trust_score: u64,                   // Trust score (scaled by 1e8)
        last_performance: u64,              // Performance score (scaled by 1e8)
        accumulated_rewards: u64,           // Total accumulated rewards
        last_update_time: u64,             // Last update timestamp
        performance_history_hash: String,  // Performance history hash
        wallet_addr_hash: String,          // Wallet address hash
        status: u64,                       // Status: 0=inactive, 1=active, 2=suspended
        registration_time: u64,            // Registration timestamp
        api_endpoint: String,              // API endpoint URL
        weight: u64,                       // Consensus weight (scaled by 1e8)
    }

    /// Full Miner info with all ModernTensor fields
    struct MinerInfo has key, copy, drop {
        uid: String,                        // Unique identifier
        subnet_uid: u64,                    // Subnet ID
        stake: u64,                         // Stake amount in octas
        trust_score: u64,                   // Trust score (scaled by 1e8)
        last_performance: u64,              // Performance score (scaled by 1e8)
        accumulated_rewards: u64,           // Total accumulated rewards
        last_update_time: u64,             // Last update timestamp
        performance_history_hash: String,  // Performance history hash
        wallet_addr_hash: String,          // Wallet address hash
        status: u64,                       // Status: 0=inactive, 1=active, 2=suspended
        registration_time: u64,            // Registration timestamp
        api_endpoint: String,              // API endpoint URL
        weight: u64,                       // Consensus weight (scaled by 1e8)
    }

    /// Register as a validator with full data structure
    public entry fun register_validator(
        account: &signer,
        uid: String,
        subnet_uid: u64,
        stake_amount: u64,
        api_endpoint: String,
        wallet_addr_hash: String,
    ) {
        let account_addr = signer::address_of(account);
        
        // Check if already registered
        assert!(!exists<ValidatorInfo>(account_addr), E_ALREADY_REGISTERED);
        
        // Check fungible asset balance (APT converted to FA)
        let balance = coin::balance<AptosCoin>(account_addr);
        assert!(balance >= stake_amount, E_NOT_ENOUGH_BALANCE);
        
        let current_time = timestamp::now_seconds();
        
        // Store validator info with complete data structure
        move_to(account, ValidatorInfo {
            uid,
            subnet_uid,
            stake: stake_amount,
            trust_score: 100_000_000,          // Default: 1.0 (scaled by 1e8)
            last_performance: 0,               // No performance yet
            accumulated_rewards: 0,            // No rewards yet
            last_update_time: current_time,
            performance_history_hash: std::string::utf8(b""),  // Empty initially
            wallet_addr_hash,
            status: 1,                         // 1 = active
            registration_time: current_time,
            api_endpoint,
            weight: 100_000_000,              // Default: 1.0 (scaled by 1e8)
        });
    }

    /// Register as a miner with full data structure
    public entry fun register_miner(
        account: &signer,
        uid: String,
        subnet_uid: u64,
        stake_amount: u64,
        api_endpoint: String,
        wallet_addr_hash: String,
    ) {
        let account_addr = signer::address_of(account);
        
        // Check if already registered
        assert!(!exists<MinerInfo>(account_addr), E_ALREADY_REGISTERED);
        
        // Check fungible asset balance (APT converted to FA)
        let balance = coin::balance<AptosCoin>(account_addr);
        assert!(balance >= stake_amount, E_NOT_ENOUGH_BALANCE);
        
        let current_time = timestamp::now_seconds();
        
        // Store miner info with complete data structure
        move_to(account, MinerInfo {
            uid,
            subnet_uid,
            stake: stake_amount,
            trust_score: 100_000_000,          // Default: 1.0 (scaled by 1e8)
            last_performance: 0,               // No performance yet
            accumulated_rewards: 0,            // No rewards yet
            last_update_time: current_time,
            performance_history_hash: std::string::utf8(b""),  // Empty initially
            wallet_addr_hash,
            status: 1,                         // 1 = active
            registration_time: current_time,
            api_endpoint,
            weight: 100_000_000,              // Default: 1.0 (scaled by 1e8)
        });
    }

    /// Update validator performance and metrics
    public entry fun update_validator_performance(
        _admin: &signer,  // Only admin should call this
        validator_addr: address,
        trust_score: u64,
        performance: u64,
        rewards: u64,
        performance_hash: String,
        weight: u64,
    ) acquires ValidatorInfo {
        assert!(exists<ValidatorInfo>(validator_addr), E_NOT_REGISTERED);
        
        let validator_info = borrow_global_mut<ValidatorInfo>(validator_addr);
        validator_info.trust_score = trust_score;
        validator_info.last_performance = performance;
        validator_info.accumulated_rewards = validator_info.accumulated_rewards + rewards;
        validator_info.performance_history_hash = performance_hash;
        validator_info.weight = weight;
        validator_info.last_update_time = timestamp::now_seconds();
    }

    /// Update miner performance and metrics
    public entry fun update_miner_performance(
        _admin: &signer,  // Only admin should call this
        miner_addr: address,
        trust_score: u64,
        performance: u64,
        rewards: u64,
        performance_hash: String,
        weight: u64,
    ) acquires MinerInfo {
        assert!(exists<MinerInfo>(miner_addr), E_NOT_REGISTERED);
        
        let miner_info = borrow_global_mut<MinerInfo>(miner_addr);
        miner_info.trust_score = trust_score;
        miner_info.last_performance = performance;
        miner_info.accumulated_rewards = miner_info.accumulated_rewards + rewards;
        miner_info.performance_history_hash = performance_hash;
        miner_info.weight = weight;
        miner_info.last_update_time = timestamp::now_seconds();
    }

    #[view]
    public fun get_validator_info(validator_addr: address): ValidatorInfo acquires ValidatorInfo {
        assert!(exists<ValidatorInfo>(validator_addr), E_NOT_REGISTERED);
        *borrow_global<ValidatorInfo>(validator_addr)
    }

    #[view]
    public fun get_miner_info(miner_addr: address): MinerInfo acquires MinerInfo {
        assert!(exists<MinerInfo>(miner_addr), E_NOT_REGISTERED);
        *borrow_global<MinerInfo>(miner_addr)
    }

    #[view]
    public fun is_validator(addr: address): bool {
        exists<ValidatorInfo>(addr)
    }

    #[view]
    public fun is_miner(addr: address): bool {
        exists<MinerInfo>(addr)
    }

    #[view]
    public fun get_validator_weight(addr: address): u64 acquires ValidatorInfo {
        if (exists<ValidatorInfo>(addr)) {
            borrow_global<ValidatorInfo>(addr).weight
        } else {
            0
        }
    }

    #[view]
    public fun get_miner_weight(addr: address): u64 acquires MinerInfo {
        if (exists<MinerInfo>(addr)) {
            borrow_global<MinerInfo>(addr).weight
        } else {
            0
        }
    }
} 