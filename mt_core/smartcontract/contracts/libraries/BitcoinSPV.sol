// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title BitcoinSPV
 * @dev Library for Bitcoin Simplified Payment Verification (SPV) proofs
 * Enables verification of Bitcoin transactions without running a full node
 */
library BitcoinSPV {
    // Bitcoin constants
    uint256 constant BITCOIN_DIFFICULTY_PERIOD = 2016; // blocks
    uint256 constant TARGET_TIMESPAN = 14 * 24 * 60 * 60; // 2 weeks in seconds
    uint256 constant MIN_DIFFICULTY = 0x1d00ffff; // minimum difficulty target

    // Error messages
    string constant ERR_INVALID_MERKLE_PROOF = "Invalid merkle proof";
    string constant ERR_INVALID_BLOCK_HEADER = "Invalid block header";
    string constant ERR_INSUFFICIENT_WORK = "Insufficient proof of work";
    string constant ERR_INVALID_TRANSACTION = "Invalid transaction format";

    struct BitcoinBlockHeader {
        uint32 version;
        bytes32 previousBlockHash;
        bytes32 merkleRoot;
        uint32 timestamp;
        uint32 difficulty;
        uint32 nonce;
        bytes32 blockHash;
    }

    struct BitcoinTransaction {
        bytes32 txHash;
        bytes rawTransaction;
        uint256 outputIndex;
        uint256 outputValue;
        bytes outputScript;
        uint256 lockTime;
        bool isTimeLocked;
    }

    struct MerkleProof {
        bytes32[] merkleProof;
        uint256 txIndex;
        bytes32 merkleRoot;
    }

    /**
     * @dev Verify Bitcoin transaction inclusion in block using SPV proof
     * @param transaction The Bitcoin transaction to verify
     * @param blockHeader The Bitcoin block header containing the transaction
     * @param merkleProof Merkle proof showing transaction inclusion
     * @return bool True if transaction is valid and included in block
     */
    function verifyTransactionInclusion(
        BitcoinTransaction memory transaction,
        BitcoinBlockHeader memory blockHeader,
        MerkleProof memory merkleProof
    ) internal pure returns (bool) {
        // 1. Verify transaction hash matches
        bytes32 computedTxHash = doubleSha256(transaction.rawTransaction);
        require(computedTxHash == transaction.txHash, ERR_INVALID_TRANSACTION);

        // 2. Verify merkle proof
        require(
            verifyMerkleProof(
                transaction.txHash,
                merkleProof.merkleProof,
                merkleProof.txIndex,
                merkleProof.merkleRoot
            ),
            ERR_INVALID_MERKLE_PROOF
        );

        // 3. Verify merkle root matches block header
        require(
            blockHeader.merkleRoot == merkleProof.merkleRoot,
            ERR_INVALID_BLOCK_HEADER
        );

        // 4. Verify block header hash
        require(verifyBlockHeader(blockHeader), ERR_INVALID_BLOCK_HEADER);

        return true;
    }

    /**
     * @dev Verify Bitcoin block header proof of work
     * @param header The Bitcoin block header to verify
     * @return bool True if header has valid proof of work
     */
    function verifyBlockHeader(
        BitcoinBlockHeader memory header
    ) internal pure returns (bool) {
        // Reconstruct block header bytes
        bytes memory headerBytes = abi.encodePacked(
            header.version,
            header.previousBlockHash,
            header.merkleRoot,
            header.timestamp,
            header.difficulty,
            header.nonce
        );

        // Compute block hash (double SHA-256)
        bytes32 computedHash = doubleSha256(headerBytes);

        // Verify computed hash matches stored hash
        if (computedHash != header.blockHash) {
            return false;
        }

        // Verify proof of work (hash must be less than target)
        uint256 target = difficultyToTarget(header.difficulty);
        return uint256(computedHash) < target;
    }

    /**
     * @dev Verify merkle proof for transaction inclusion
     * @param txHash Transaction hash to verify
     * @param proof Array of merkle proof hashes
     * @param index Transaction index in block
     * @param merkleRoot Expected merkle root
     * @return bool True if proof is valid
     */
    function verifyMerkleProof(
        bytes32 txHash,
        bytes32[] memory proof,
        uint256 index,
        bytes32 merkleRoot
    ) internal pure returns (bool) {
        bytes32 computedHash = txHash;

        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];

            if (index % 2 == 0) {
                // If index is even, hash is on the left
                computedHash = doubleSha256(
                    abi.encodePacked(computedHash, proofElement)
                );
            } else {
                // If index is odd, hash is on the right
                computedHash = doubleSha256(
                    abi.encodePacked(proofElement, computedHash)
                );
            }

            index = index / 2;
        }

        return computedHash == merkleRoot;
    }

    /**
     * @dev Verify Bitcoin timelock (CLTV - CheckLockTimeVerify)
     * @param transaction Bitcoin transaction with timelock
     * @param currentBlockHeight Current Bitcoin block height
     * @param currentTimestamp Current timestamp
     * @return bool True if timelock has expired
     */
    function verifyTimelock(
        BitcoinTransaction memory transaction,
        uint256 currentBlockHeight,
        uint256 currentTimestamp
    ) internal pure returns (bool) {
        if (!transaction.isTimeLocked) {
            return true; // No timelock, always valid
        }

        if (transaction.lockTime < 500000000) {
            // Lock time is block height
            return currentBlockHeight >= transaction.lockTime;
        } else {
            // Lock time is timestamp
            return currentTimestamp >= transaction.lockTime;
        }
    }

    /**
     * @dev Extract and verify Bitcoin staking output
     * @param transaction Bitcoin transaction containing staking output
     * @param stakingScript Expected staking script pattern
     * @param minAmount Minimum staking amount required
     * @return stakingAmount Amount being staked
     * @return isValid True if staking output is valid
     */
    function verifyStakingOutput(
        BitcoinTransaction memory transaction,
        bytes memory stakingScript,
        uint256 minAmount
    ) internal pure returns (uint256 stakingAmount, bool isValid) {
        // Parse transaction outputs to find staking output
        // This is simplified - in practice would need full transaction parsing

        if (transaction.outputValue < minAmount) {
            return (0, false);
        }

        // Verify output script matches expected staking pattern
        if (keccak256(transaction.outputScript) != keccak256(stakingScript)) {
            return (0, false);
        }

        return (transaction.outputValue, true);
    }

    /**
     * @dev Double SHA-256 hash function (Bitcoin's hash function)
     * @param data Data to hash
     * @return bytes32 Double SHA-256 hash
     */
    function doubleSha256(bytes memory data) internal pure returns (bytes32) {
        return sha256(abi.encodePacked(sha256(data)));
    }

    /**
     * @dev Convert Bitcoin difficulty bits to target value
     * @param difficulty Bitcoin difficulty bits (compact format)
     * @return uint256 Target value for proof of work
     */
    function difficultyToTarget(
        uint32 difficulty
    ) internal pure returns (uint256) {
        uint256 exponent = difficulty >> 24;
        uint256 mantissa = difficulty & 0xffffff;

        if (exponent <= 3) {
            return mantissa >> (8 * (3 - exponent));
        } else {
            return mantissa << (8 * (exponent - 3));
        }
    }

    /**
     * @dev Validate Bitcoin address format
     * @param bitcoinAddress Bitcoin address to validate
     * @return bool True if address format is valid
     */
    function validateBitcoinAddress(
        string memory bitcoinAddress
    ) internal pure returns (bool) {
        bytes memory addr = bytes(bitcoinAddress);

        // Basic validation - check length and first character
        if (addr.length < 26 || addr.length > 35) {
            return false;
        }

        // Check address type prefixes
        if (addr[0] == bytes1("1")) {
            // P2PKH address
            return addr.length >= 26 && addr.length <= 35;
        } else if (addr[0] == bytes1("3")) {
            // P2SH address
            return addr.length >= 26 && addr.length <= 35;
        } else if (
            addr[0] == bytes1("b") &&
            addr[1] == bytes1("c") &&
            addr[2] == bytes1("1")
        ) {
            // Bech32 address
            return addr.length >= 42 && addr.length <= 62;
        }

        return false;
    }

    /**
     * @dev Calculate Bitcoin transaction fee
     * @param inputValue Total input value
     * @param outputValue Total output value
     * @return uint256 Transaction fee (input - output)
     */
    function calculateTransactionFee(
        uint256 inputValue,
        uint256 outputValue
    ) internal pure returns (uint256) {
        require(
            inputValue >= outputValue,
            "Invalid transaction: inputs < outputs"
        );
        return inputValue - outputValue;
    }
}
