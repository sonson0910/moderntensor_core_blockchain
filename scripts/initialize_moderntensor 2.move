script {
    use moderntensor::miner;
    use moderntensor::validator;
    use moderntensor::subnet;
    use std::string;
    
    /// Script to initialize necessary registries for ModernTensor
    fun initialize_moderntensor(owner: signer) {
        // Initialize registry for subnet
        subnet::initialize_registry(&owner);
        
        // Initialize registry for miner
        miner::initialize_registry(&owner);
        
        // Initialize registry for validator
        validator::initialize_registry(&owner);
        
        // Next, create a default subnet
        subnet::create_subnet(
            &owner,
            1, // Subnet UID 1 - default
            string::utf8(b"Default Subnet"),
            string::utf8(b"Default subnet for ModernTensor testing"),
            1000, // Max miners
            100,  // Max validators
            86400, // Immunity period (1 day in seconds)
            10000000, // Min stake for miners (10 APT)
            50000000, // Min stake for validators (50 APT)
            1000000,  // Registration cost (1 APT)
        );
    }
} 