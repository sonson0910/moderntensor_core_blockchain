script {
    use moderntensor::miner;
    use std::string;
    
    /// Script to register a new miner to ModernTensor
    fun register_miner(account: signer, uid_hex: vector<u8>, subnet_uid: u64, api_url: vector<u8>, stake_amount: u64) {
        // Convert API URL to string
        let api_endpoint = string::utf8(api_url);
        
        // Register miner with the specified parameters
        miner::register_miner(
            &account,
            uid_hex,
            subnet_uid,
            stake_amount,
            api_endpoint
        );
    }
} 