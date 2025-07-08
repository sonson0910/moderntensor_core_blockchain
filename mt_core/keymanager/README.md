# ModernTensor Aptos Key Management

This module provides tools for managing Aptos account keys, including:

- **ColdKeyManager**: Creates and manages coldkeys with encrypted mnemonics
- **HotKeyManager**: Creates and manages hotkeys derived from coldkeys
- **Utilities**: For encryption/decryption and key access

All keys are securely stored using Fernet encryption with password-based key derivation.

--gen coldkey
mtcli w create-coldkey --name kickoff --base-dir "moderntensor"
--gen hotkey
mtcli w generate-hotkey --coldkey kickoff --hotkey-name hk1 --base-dir "moderntensor"
pass 123456