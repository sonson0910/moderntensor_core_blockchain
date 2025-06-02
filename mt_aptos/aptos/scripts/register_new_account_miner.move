script {
    use moderntensor::miner;
    use std::string;
    
    /// Script to register a new miner to ModernTensor
    fun register_new_account_miner(account: signer) {
        // Register miner with the specified parameters
        miner::register_miner(
            &account,
            b"miner003", // UID as bytes (different from previous)
            1,           // Subnet UID (the one we created)
            10000000,    // Stake amount (10 APT)
            string::utf8(b"http://example.com/miner3") // Different API endpoint
        );
    }
} 