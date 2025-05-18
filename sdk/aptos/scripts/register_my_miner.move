script {
    use moderntensor::miner;
    use std::string;
    
    /// Script to register a new miner to ModernTensor
    fun register_my_miner(account: signer) {
        // Register miner with the specified parameters
        miner::register_miner(
            &account,
            b"miner001", // UID as bytes
            1,           // Subnet UID (the one we just created)
            10000000,    // Stake amount (10 APT)
            string::utf8(b"http://localhost:8000") // Example API endpoint
        );
    }
} 