script {
    use moderntensor::validator;
    use std::string;
    
    /// Script to register a new validator to ModernTensor
    fun register_my_validator(account: signer) {
        // Register validator with the specified parameters
        validator::register_validator(
            &account,
            b"validator001", // UID as bytes
            1,               // Subnet UID (the one we just created)
            50000000,        // Stake amount (50 APT)
            string::utf8(b"http://localhost:9000") // Example API endpoint
        );
    }
} 