script {
    use moderntensor::validator;
    use std::string;
    
    /// Script to register a new validator to ModernTensor
    fun register_new_account_validator(account: signer) {
        // Register validator with the specified parameters
        validator::register_validator(
            &account,
            b"validator003", // UID as bytes (different from previous)
            1,               // Subnet UID (the one we created)
            50000000,        // Stake amount (50 APT)
            string::utf8(b"http://example.com/validator3") // Different API endpoint
        );
    }
} 