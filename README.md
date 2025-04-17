# ModernTensor ✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Or Apache 2.0, depending on your choice -->

**ModernTensor** is a decentralized machine intelligence network built on the Cardano blockchain, inspired by the architecture and vision of Bittensor. The project aims to create an open marketplace for AI/ML services, where models compete and are rewarded based on their performance and contribution value to the network, leveraging Cardano's unique features like the EUTXO model and native assets.

![moderntensor.png](https://github.com/sonson0910/moderntensor/blob/main/moderntensor.png)

## 🚀 Introduction

In the ModernTensor ecosystem:

*   **Miners:** Provide AI/ML services/models via API endpoints. They register their hotkey (representing the miner's identifier - UID) onto the network.
*   **Validators:** (Future) Evaluate the quality and performance of Miners, contributing to the consensus mechanism and reward distribution.
*   **Cardano Blockchain:** Serves as the secure and decentralized foundation layer to record the network state (miner registrations, stake, rewards, etc.) through smart contracts (Plutus).

This project includes an SDK toolkit and a command-line interface (CLI) for interacting with the network.

## 📋 Current Features

*   **Wallet Management CLI (`mtcli w`):**
    *   Create Coldkey (`create-coldkey`): Generates a secure mnemonic phrase and encrypts it for storing the root key.
    *   Restore Coldkey (`restore-coldkey`): Recreates a coldkey from a saved mnemonic phrase.
    *   Generate Hotkey (`generate-hotkey`): Generates child keys (hotkeys) from the coldkey using standard HD derivation, used for Miner identification and signing operational transactions.
    *   Import Hotkey (`import-hotkey`): Imports an encrypted hotkey from an external source.
    *   Regenerate Hotkey (`regen-hotkey`): Recovers hotkey information if the `hotkeys.json` file is lost, requiring only the coldkey and the derivation index.
    *   List Wallets (`list`): Displays a list of coldkeys and their corresponding hotkeys.
    *   Register Hotkey (`register-hotkey`): Registers a hotkey as a Miner on the ModernTensor network, creating/updating a UTxO at the smart contract address with Miner information (UID, stake, API endpoint,...).

## 💡 Using the CLI (`mtcli`)

The main command-line tool is `mtcli`. The `w` (`wallet`) subcommand is used for wallet management, `tx` for transactions, and `query` for blockchain information.

**Help:**
```bash
mtcli --help
mtcli w --help
mtcli tx --help
mtcli query --help
mtcli w <command_name> --help # Example: mtcli w create-coldkey --help
mtcli query <command_name> --help # Example: mtcli query address --help
```

### Wallet Commands (`mtcli w`)

**Examples:**

```bash
# 1. Create a new coldkey named 'my_main_coldkey'
mtcli w create-coldkey --name my_main_coldkey

# 2. Generate a new hotkey named 'miner_hk1' from the coldkey above
# (You will be prompted for the coldkey password)
mtcli w generate-hotkey --coldkey my_main_coldkey --hotkey-name miner_hk1

# 3. List all wallets
mtcli w list

# 4. Register hotkey 'miner_hk1' as a miner on subnet 1
# (You will be prompted for the coldkey password)
mtcli w register-hotkey \
    --coldkey my_main_coldkey \
    --hotkey miner_hk1 \
    --subnet-uid 1 \
    --initial-stake 5000000 \
    --api-endpoint "http://123.45.67.89:8080" \
    --network testnet # or mainnet

# 5. Restore a coldkey from mnemonic (if needed)
mtcli w restore-coldkey --name recovered_coldkey --mnemonic "word1 word2 ... word24"

# 6. Regenerate hotkey 'miner_hk1' if hotkeys.json is lost (knowing the index is 0)
mtcli w regen-hotkey --coldkey my_main_coldkey --hotkey-name miner_hk1 --index 0

# 7. Show the derived address for a hotkey
# (You will be prompted for the coldkey password)
mtcli w show-address --coldkey my_main_coldkey --hotkey miner_hk1
```

### Transaction Commands (`mtcli tx`)

**Examples:**

```bash
# Send 5 ADA from kickoff/hk1 to another address on testnet
# (You will be prompted for the coldkey password)
mtcli tx send \
    --coldkey kickoff \
    --hotkey hk1 \
    --to <recipient_address> \
    --amount 5000000 \
    --network testnet

# Send 100 units of a specific token from kickoff/hk1 to wallet2/hk2 on testnet
# (You will be prompted for the coldkey password)
mtcli tx send \
    --coldkey kickoff \
    --hotkey hk1 \
    --to wallet2/hk2 \
    --amount 100 \
    --token <policy_id_hex>.<asset_name_hex> \
    --network testnet
```

### Query Commands (`mtcli query`)

**Examples:**

```bash
# 1. Get detailed info (ADA, tokens, UTxO count) for a specific Cardano address
mtcli query address <cardano_address>

# 2. Get the balance (ADA, tokens) for a specific hotkey
# (You will be prompted for the coldkey password)
mtcli query balance --coldkey <coldkey_name> --hotkey <hotkey_name>

# 3. List the UTxOs held by a specific hotkey address
# (You will be prompted for the coldkey password)
mtcli query utxos --coldkey <coldkey_name> --hotkey <hotkey_name>

# 4. (Advanced) Find a specific UTxO at a smart contract address using its UID (hex)
# This assumes the datum format is MinerDatum
mtcli query contract-utxo --contract-address <contract_address> --uid <miner_uid_hex>

# 5. (Advanced) Find the UTxO with the lowest performance score at a smart contract address
# This assumes the datum format is MinerDatum
mtcli query lowest-performance --contract-address <contract_address>
```

### Staking Commands (`mtcli stake`)

**Examples:**

```bash
# 1. Delegate stake for a specific hotkey to a pool
# (Requires the hotkey to have been generated with a stake key)
# (You will be prompted for the coldkey password)
mtcli stake delegate --coldkey <coldkey_name> --hotkey <hotkey_name> --pool-id <pool_id_bech32_or_hex>

# 2. Change delegation to a different pool
# (You will be prompted for the coldkey password)
mtcli stake redelegate --coldkey <coldkey_name> --hotkey <hotkey_name> --pool-id <new_pool_id>

# 3. Withdraw available staking rewards for the hotkey's stake address
# (You will be prompted for the coldkey password)
mtcli stake withdraw --coldkey <coldkey_name> --hotkey <hotkey_name>

# 4. Show staking information (delegated pool, rewards) for the hotkey's stake address
# (You will be prompted for the coldkey password)
mtcli stake info --coldkey <coldkey_name> --hotkey <hotkey_name>
```

## 🏗️ Architecture (Preliminary)

*   `sdk/`: Core toolkit (Python SDK)
    *   `keymanager/`: Logic for managing coldkeys, hotkeys, encryption, derivation.
    *   `cli/`: Command-line interface (`mtcli`).
    *   `service/`: High-level interaction services (e.g., key registration).
    *   `smartcontract/`: Interaction with Plutus scripts (reading, transaction building).
    *   `metagraph/`: Logic related to network state (datum, hashing,...).
    *   `config/`: Project configuration.
    *   `consensus/`, `agent/`: (Potential) Components related to consensus and agent behavior.
*   `contracts/`: (Potential) Location for Plutus script source code.
*   `README.md`: This documentation.
*   `requirements.txt`: List of required Python libraries.
*   `.env`, `settings.toml`: (Potential) Environment configuration files.

## ⚙️ Installation

1.  **Requirements:**
    *   Python 3.9+
    *   pip

2.  **Clone Repository:**
    ```bash
    git clone <your_repository_url>
    cd moderntensor
    ```

3.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate   # On Windows
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure you have a complete `requirements.txt` file with libraries like `click`, `rich`, `pycardano`, `blockfrost-python`, `cbor2`, `cryptography`, etc...)*

5.  **(Optional) Install in Editable Mode:** If you want the `mtcli` CLI to be runnable from anywhere and reflect code changes immediately. Requires a suitable `setup.py` or `pyproject.toml` file.
    ```bash
    pip install -e .
    ```

## 🤝 Contributing

We welcome contributions from the community! Please refer to `CONTRIBUTING.md` (if available) or follow standard procedures:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file (if available) for details. (Or change to your chosen license, e.g., Apache 2.0)

## 📞 Contact

(Optional: Add contact information, Discord links, Twitter, etc.)
