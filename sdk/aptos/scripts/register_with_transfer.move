script {
    use aptos_framework::coin;
    use aptos_framework::aptos_coin::AptosCoin;
    use aptos_framework::signer;
    
    /// Script to transfer tokens to a new miner account
    fun register_with_transfer(
        source_account: signer, 
        receiver_address: address,
        amount: u64
    ) {
        // Transfer APT to the receiver
        coin::transfer<AptosCoin>(&source_account, receiver_address, amount);
    }
} 