script {
    use moderntensor::subnet;
    use std::string;
    
    /// Script to create a default subnet
    fun create_subnet(owner: signer) {
        // Create a default subnet
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