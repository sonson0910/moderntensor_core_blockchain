# Import Path Analysis Report

Generated for: moderntensor_aptos

⚠️ Found import issues in 34 files:

## verify_improvements.py

**Line 51:**
```python
from mt_core.config.config_loader import get_config
```
**Should be:**
```python
from mt_core.config.config_loader from scripts import get_config
```

**Line 160:**
```python
from mt_core.config.config_loader import get_blockchain_config
```
**Should be:**
```python
from mt_core.config.config_loader from scripts import get_blockchain_config
```

## mt_core/async_client.py

**Line 15:**
```python
from .config.config_loader import get_config
```
**Should be:**
```python
from .config.config_loader from scripts import get_config
```

## scripts/prepare_testnet_datums.py

**Line 36:**
```python
from mt_aptos.metagraph.create_utxo import find_suitable_ada_input  # Dùng lại hàm này
```
**Should be:**
```python
from mt_aptos.metagraph.create_utxo from scripts import find_suitable_ada_input  # Dùng lại hàm này
```

**Line 42:**
```python
from mt_aptos.service.context import get_chain_context  # Lấy context trực tiếp
```
**Should be:**
```python
from mt_aptos.service.context from scripts import get_chain_context  # Lấy context trực tiếp
```

## backup/verify_improvements.py

**Line 51:**
```python
from mt_core.config.config_loader import get_config
```
**Should be:**
```python
from mt_core.config.config_loader from scripts import get_config
```

**Line 160:**
```python
from mt_core.config.config_loader import get_blockchain_config
```
**Should be:**
```python
from mt_core.config.config_loader from scripts import get_blockchain_config
```

## tests/integration/test_full_blockchain_flow.py

**Line 28:**
```python
from tests.conftest from tests import test_private_keys
```
**Should be:**
```python
from tests.conftest from tests from tests import test_private_keys
```

## mt_aptos/aptos_core/account_service.py

**Line 16:**
```python
from .address import get_aptos_address
```
**Should be:**
```python
from .address from scripts import get_aptos_address
```

## mt_aptos/aptos_core/__init__.py

**Line 7:**
```python
from .context import get_aptos_context
```
**Should be:**
```python
from .context from scripts import get_aptos_context
```

**Line 8:**
```python
from .address import get_aptos_address
```
**Should be:**
```python
from .address from scripts import get_aptos_address
```

## mt_aptos/aptos_core/contract_client.py

**Line 199:**
```python
from mt_aptos.metagraph.metagraph_data import get_all_miner_data
```
**Should be:**
```python
from mt_aptos.metagraph.metagraph_data from scripts import get_all_miner_data
```

**Line 218:**
```python
from mt_aptos.metagraph.metagraph_data import get_all_validator_data
```
**Should be:**
```python
from mt_aptos.metagraph.metagraph_data from scripts import get_all_validator_data
```

## mt_aptos/consensus/validator_node_core.py

**Line 32:**
```python
from ..monitoring.metrics import get_metrics_manager
```
**Should be:**
```python
from ..monitoring.metrics from scripts import get_metrics_manager
```

**Line 290:**
```python
from ..aptos_core.validator_helper import get_all_validators, get_all_miners
```
**Should be:**
```python
from ..aptos_core.validator_helper from scripts import get_all_validators, get_all_miners
```

## mt_aptos/consensus/state.py

**Line 19:**
```python
from ..metagraph.metagraph_data import get_all_validator_data
```
**Should be:**
```python
from ..metagraph.metagraph_data from scripts import get_all_validator_data
```

## mt_aptos/cli/wallet_cli.py

**Line 30:**
```python
# from mt_aptos.utils.cardano_utils import get_current_slot # Replace with Aptos utility if needed
```
**Should be:**
```python
# from mt_aptos.utils.cardano_utils from scripts import get_current_slot # Replace with Aptos utility if needed
```

## mt_aptos/keymanager/__init__.py

**Line 8:**
```python
from .encryption_utils import get_cipher_suite, get_or_create_salt, generate_encryption_key
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite, get_or_create_salt, generate_encryption_key
```

## mt_aptos/keymanager/decryption_utils.py

**Line 11:**
```python
from .encryption_utils import get_or_create_salt, generate_encryption_key
```
**Should be:**
```python
from .encryption_utils from scripts import get_or_create_salt, generate_encryption_key
```

## mt_aptos/keymanager/coldkey_manager.py

**Line 14:**
```python
from .encryption_utils import get_cipher_suite
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite
```

## mt_aptos/keymanager/hd_wallet_manager.py

**Line 25:**
```python
from .encryption_utils import get_cipher_suite
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite
```

## mt_aptos/network/app/main.py

**Line 19:**
```python
from mt_aptos.aptos_core.context import get_aptos_context
```
**Should be:**
```python
from mt_aptos.aptos_core.context from scripts import get_aptos_context
```

## mt_aptos/network/app/api/v1/endpoints/consensus.py

**Line 16:**
```python
from mt_aptos.network.app.dependencies import get_validator_node
```
**Should be:**
```python
from mt_aptos.network.app.dependencies from scripts import get_validator_node
```

## mt_aptos/network/app/api/v1/endpoints/validator_health.py

**Line 16:**
```python
from ....dependencies import get_validator_node
```
**Should be:**
```python
from ....dependencies from scripts import get_validator_node
```

## mt_aptos/network/app/api/v1/endpoints/miner_comms.py

**Line 11:**
```python
from mt_aptos.network.app.dependencies import get_validator_node
```
**Should be:**
```python
from mt_aptos.network.app.dependencies from scripts import get_validator_node
```

## mt_core/consensus/validator_node_core.py

**Line 27:**
```python
from ..config.config_loader import get_config
```
**Should be:**
```python
from ..config.config_loader from scripts import get_config
```

**Line 37:**
```python
from ..monitoring.metrics import get_metrics_manager
```
**Should be:**
```python
from ..monitoring.metrics from scripts import get_metrics_manager
```

## mt_core/consensus/consensus_blockchain.py

**Line 13:**
```python
from ..config.config_loader import get_config
```
**Should be:**
```python
from ..config.config_loader from scripts import get_config
```

## mt_core/consensus/validator_node_refactored.py

**Line 35:**
```python
from ..config.config_loader import get_config
```
**Should be:**
```python
from ..config.config_loader from scripts import get_config
```

## mt_core/consensus/state.py

**Line 38:**
```python
from ..config.config_loader import get_config
```
**Should be:**
```python
from ..config.config_loader from scripts import get_config
```

**Line 56:**
```python
from ..metagraph.metagraph_data import get_all_validator_data
```
**Should be:**
```python
from ..metagraph.metagraph_data from scripts import get_all_validator_data
```

## mt_core/monitoring/health.py

**Line 11:**
```python
from ..config.config_loader import get_config
```
**Should be:**
```python
from ..config.config_loader from scripts import get_config
```

## mt_core/core_client/account_service.py

**Line 16:**
```python
from .address import get_aptos_address
```
**Should be:**
```python
from .address from scripts import get_aptos_address
```

## mt_core/core_client/__init__.py

**Line 10:**
```python
from .context import get_core_context
```
**Should be:**
```python
from .context from scripts import get_core_context
```

**Line 20:**
```python
from .address import get_core_address
```
**Should be:**
```python
from .address from scripts import get_core_address
```

## mt_core/keymanager/__init__.py

**Line 8:**
```python
from .encryption_utils import get_cipher_suite, get_or_create_salt, generate_encryption_key
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite, get_or_create_salt, generate_encryption_key
```

## mt_core/keymanager/decryption_utils.py

**Line 11:**
```python
from .encryption_utils import get_or_create_salt, generate_encryption_key
```
**Should be:**
```python
from .encryption_utils from scripts import get_or_create_salt, generate_encryption_key
```

## mt_core/keymanager/coldkey_manager.py

**Line 14:**
```python
from .encryption_utils import get_cipher_suite
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite
```

## mt_core/keymanager/hd_wallet_manager.py

**Line 25:**
```python
from .encryption_utils import get_cipher_suite
```
**Should be:**
```python
from .encryption_utils from scripts import get_cipher_suite
```

## mt_core/network/app/main.py

**Line 19:**
```python
# from mt_aptos.aptos_core.context import get_aptos_context
```
**Should be:**
```python
# from mt_aptos.aptos_core.context from scripts import get_aptos_context
```

## mt_core/network/app/api/v1/endpoints/consensus.py

**Line 30:**
```python
from mt_core.network.app.dependencies import get_validator_node
```
**Should be:**
```python
from mt_core.network.app.dependencies from scripts import get_validator_node
```

## mt_core/network/app/api/v1/endpoints/validator_health.py

**Line 16:**
```python
from moderntensor_aptos.mt_core.network.app.dependencies import get_validator_node
```
**Should be:**
```python
from moderntensor_aptos.mt_core.network.app.dependencies from scripts import get_validator_node
```

## mt_core/network/app/api/v1/endpoints/miner_comms.py

**Line 11:**
```python
from mt_core.network.app.dependencies import get_validator_node
```
**Should be:**
```python
from mt_core.network.app.dependencies from scripts import get_validator_node
```

