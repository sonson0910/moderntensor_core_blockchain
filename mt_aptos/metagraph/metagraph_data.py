# sdk/metagraph/metagraph_data.py
import logging
from typing import List, Dict, Any, Optional, Type, Tuple, DefaultDict
from collections import defaultdict  # Import defaultdict
from pycardano import (
    Address,
    BlockFrostChainContext,
    UTxO,
    PlutusData,
    ScriptHash,
    Network,
)
import cbor2  # Vẫn cần cho trường hợp datum không chuẩn
import asyncio

from mt_aptos.async_client import RestClient

# Import các lớp Datum đã cập nhật
from .metagraph_datum import (
    MinerData,
    ValidatorData,
    SubnetDynamicData,
    SubnetStaticData,
    from_move_resource
)

logger = logging.getLogger(__name__)


# --- Functions to get data for Miners ---
async def get_all_miner_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all miner data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a miner.
        Returns an empty list if no miners are found or if an error occurs.
    """
    logger.info(f"Fetching Miner data from contract: {contract_address}")

    try:
        # Call the view function to get all miners from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_miners",
            []
        )
        
        logger.info(f"Found {len(results)} miners in contract")
        
        # Process each miner's data into our expected format
        processed_miners = []
        for miner_resource in results:
            try:
                # Convert resource to our data model
                miner_data = {
                    "uid": miner_resource.get("uid", ""),
                    "subnet_uid": int(miner_resource.get("subnet_uid", -1)),
                    "stake": int(miner_resource.get("stake", 0)),
                    "trust_score": float(miner_resource.get("trust_score", 0.0)),
                    "last_performance": float(miner_resource.get("last_performance", 0.0)),
                    "accumulated_rewards": int(miner_resource.get("accumulated_rewards", 0)),
                    "last_update_time": int(miner_resource.get("last_update_time", 0)),
                    "performance_history_hash": miner_resource.get("performance_history_hash", ""),
                    "wallet_addr_hash": miner_resource.get("wallet_addr_hash", ""),
                    "status": int(miner_resource.get("status", 0)),
                    "registration_time": int(miner_resource.get("registration_time", 0)),
                    "api_endpoint": miner_resource.get("api_endpoint", ""),
                    "weight": float(miner_resource.get("weight", 0.0)),
                }
                processed_miners.append(miner_data)
            except Exception as e:
                logger.warning(f"Failed to process miner data: {e}")
                logger.debug(f"Problematic miner data: {miner_resource}")
                continue
                
        return processed_miners
        
    except Exception as e:
        logger.exception(f"Failed to fetch miners from contract: {e}")
        return []


# --- Functions to get data for Validators ---
async def get_all_validator_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all validator data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a validator.
        Returns an empty list if no validators are found or if an error occurs.
    """
    logger.info(f"Fetching Validator data from contract: {contract_address}")

    try:
        # Call the view function to get all validators from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_validators",
            []
        )
        
        logger.info(f"Found {len(results)} validators in contract")
        
        # Process each validator's data into our expected format
        processed_validators = []
        for validator_resource in results:
            try:
                # Convert resource to our data model
                validator_data = {
                    "uid": validator_resource.get("uid", ""),
                    "subnet_uid": int(validator_resource.get("subnet_uid", -1)),
                    "stake": int(validator_resource.get("stake", 0)),
                    "trust_score": float(validator_resource.get("trust_score", 0.0)),
                    "last_performance": float(validator_resource.get("last_performance", 0.0)),
                    "accumulated_rewards": int(validator_resource.get("accumulated_rewards", 0)),
                    "last_update_time": int(validator_resource.get("last_update_time", 0)),
                    "performance_history_hash": validator_resource.get("performance_history_hash", ""),
                    "wallet_addr_hash": validator_resource.get("wallet_addr_hash", ""),
                    "status": int(validator_resource.get("status", 0)),
                    "registration_time": int(validator_resource.get("registration_time", 0)),
                    "api_endpoint": validator_resource.get("api_endpoint", ""),
                    "weight": float(validator_resource.get("weight", 0.0)),
                }
                processed_validators.append(validator_data)
            except Exception as e:
                logger.warning(f"Failed to process validator data: {e}")
                logger.debug(f"Problematic validator data: {validator_resource}")
                continue
                
        return processed_validators
        
    except Exception as e:
        logger.exception(f"Failed to fetch validators from contract: {e}")
        return []


# --- Functions to get data for Subnets ---
async def get_all_subnet_data(
    client: RestClient, contract_address: str
) -> List[Dict[str, Any]]:
    """
    Retrieves and processes all subnet data from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.

    Returns:
        A list of dictionaries, each containing the details of a subnet.
        Returns an empty list if no subnets are found or if an error occurs.
    """
    logger.info(f"Fetching Subnet data from contract: {contract_address}")

    try:
        # Call the view function to get all subnets from the contract
        results = await client.view_function(
            contract_address,
            "moderntensor",
            "get_all_subnets",
            []
        )
        
        logger.info(f"Found {len(results)} subnets in contract")
        
        # Process each subnet's data into our expected format
        processed_subnets = []
        for subnet_resource in results:
            try:
                # For subnets, we might have static and dynamic data combined
                subnet_data = {
                    "net_uid": int(subnet_resource.get("net_uid", -1)),
                    "name": subnet_resource.get("name", ""),
                    "owner_addr": subnet_resource.get("owner_addr", ""),
                    "max_miners": int(subnet_resource.get("max_miners", 0)),
                    "max_validators": int(subnet_resource.get("max_validators", 0)),
                    "immunity_period": int(subnet_resource.get("immunity_period", 0)),
                    "creation_time": int(subnet_resource.get("creation_time", 0)),
                    "description": subnet_resource.get("description", ""),
                    "version": int(subnet_resource.get("version", 0)),
                    "min_stake_miner": int(subnet_resource.get("min_stake_miner", 0)),
                    "min_stake_validator": int(subnet_resource.get("min_stake_validator", 0)),
                    "weight": float(subnet_resource.get("weight", 0.0)),
                    "performance": float(subnet_resource.get("performance", 0.0)),
                    "current_epoch": int(subnet_resource.get("current_epoch", 0)),
                    "registration_open": int(subnet_resource.get("registration_open", 0)),
                    "reg_cost": int(subnet_resource.get("reg_cost", 0)),
                    "incentive_ratio": float(subnet_resource.get("incentive_ratio", 0.0)),
                    "last_update_time": int(subnet_resource.get("last_update_time", 0)),
                    "total_stake": int(subnet_resource.get("total_stake", 0)),
                    "validator_count": int(subnet_resource.get("validator_count", 0)),
                    "miner_count": int(subnet_resource.get("miner_count", 0)),
                }
                processed_subnets.append(subnet_data)
            except Exception as e:
                logger.warning(f"Failed to process subnet data: {e}")
                logger.debug(f"Problematic subnet data: {subnet_resource}")
                continue
                
        return processed_subnets
        
    except Exception as e:
        logger.exception(f"Failed to fetch subnets from contract: {e}")
        return []


# --- Helper function to get single miner or validator data ---
async def get_entity_data(
    client: RestClient, 
    contract_address: str, 
    entity_type: str, 
    entity_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieves data for a single miner or validator from the Aptos blockchain.

    Args:
        client: Aptos REST client.
        contract_address: Contract address for ModernTensor.
        entity_type: Either 'miner' or 'validator'.
        entity_id: The UID of the entity to retrieve.

    Returns:
        A dictionary containing the entity's details, or None if not found.
    """
    try:
        if entity_type.lower() == 'miner':
            function_name = "get_miner"
        elif entity_type.lower() == 'validator':
            function_name = "get_validator"
        else:
            logger.error(f"Invalid entity_type: {entity_type}")
            return None
            
        # Call the view function to get the specific entity
        result = await client.view_function(
            contract_address,
            "moderntensor",
            function_name,
            [entity_id]
        )
        
        if not result:
            logger.warning(f"No {entity_type} found with ID: {entity_id}")
            return None
            
        # Process the data into our expected format (similar to get_all functions)
        # ... (similar processing as in get_all functions)
        return result
        
    except Exception as e:
        logger.exception(f"Failed to fetch {entity_type} {entity_id}: {e}")
        return None


# --- Hàm lấy dữ liệu cho Miners ---
async def get_all_miner_data_old(
    context: BlockFrostChainContext, script_hash: ScriptHash, network: Network
) -> List[Tuple[UTxO, Dict[str, Any]]]:
    """
    [DEPRECATED] Old Cardano implementation, DO NOT USE for Aptos.
    
    Lấy và decode tất cả dữ liệu MinerDatum từ các UTXO tại địa chỉ script.
    CHỈ trả về dữ liệu từ UTXO mới nhất cho mỗi UID.

    Args:
        context: Context blockchain (ví dụ: BlockFrostChainContext).
        script_hash: Script hash của smart contract chứa Datum.
        network: Mạng Cardano đang sử dụng (Network.TESTNET hoặc Network.MAINNET).

    Returns:
        Một list các tuple (UTxO, dictionary), mỗi tuple chứa thông tin chi tiết của UTXO
        mới nhất và Datum tương ứng đã được decode cho mỗi UID. Trả về list rỗng nếu
        không tìm thấy UTXO hợp lệ hoặc có lỗi xảy ra.
    """
    latest_data_list: List[Tuple[UTxO, Dict[str, Any]]] = []
    utxos_by_uid: DefaultDict[str, List[Tuple[UTxO, MinerData]]] = defaultdict(
        list
    )  # Nhóm theo UID
    contract_address = Address(payment_part=script_hash, network=network)
    logger.info(f"Fetching Miner UTxOs from address: {contract_address}")

    try:
        utxos: List[UTxO] = context.utxos(str(contract_address))
        logger.info(f"Found {len(utxos)} potential UTxOs at miner contract address.")
    except Exception as e:
        logger.exception(f"Failed to fetch UTxOs for address {contract_address}: {e}")
        return []  # Trả về list rỗng nếu không fetch được

    # 1. Decode và nhóm tất cả UTXO hợp lệ theo UID
    for utxo in utxos:
        if utxo.output.datum and utxo.output.datum.cbor:  # type: ignore[attr-defined]
            try:
                # Decode bằng phương thức của lớp MinerDatum
                decoded_datum: MinerData = MinerData.from_cbor(utxo.output.datum.cbor)  # type: ignore[assignment, attr-defined]

                uid_bytes = getattr(decoded_datum, "uid", None)
                if uid_bytes and isinstance(uid_bytes, bytes):
                    uid_hex = uid_bytes.hex()
                    utxos_by_uid[uid_hex].append((utxo, decoded_datum))
                else:
                    logger.warning(
                        f"Skipping UTxO {utxo.input} due to invalid or missing UID in decoded MinerDatum."
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to decode MinerDatum for UTxO {utxo.input}: {e}"
                )
                logger.debug(f"Datum CBOR: {utxo.output.datum.cbor.hex()}")  # type: ignore[attr-defined]
                continue  # Bỏ qua UTXO lỗi decode
        elif utxo.output.datum_hash:
            logger.debug(
                f"Skipping UTxO {utxo.input} with datum hash (inline datum required)."
            )

    # 2. Lọc và chọn UTXO mới nhất cho mỗi UID (giả định cái cuối trong list là mới nhất)
    for uid_hex, utxo_datum_list in utxos_by_uid.items():
        if not utxo_datum_list:
            continue

        # Chọn cái cuối cùng trong list, giả định nó là mới nhất
        latest_utxo, latest_decoded_datum = utxo_datum_list[-1]

        try:
            # Trích xuất thông tin từ datum mới nhất đã decode
            datum_dict = {
                "uid": uid_hex,  # Đã có từ key
                "subnet_uid": getattr(latest_decoded_datum, "subnet_uid", -1),
                "stake": getattr(latest_decoded_datum, "stake", 0),
                "last_performance": getattr(
                    latest_decoded_datum, "last_performance", 0.0
                ),
                "trust_score": getattr(latest_decoded_datum, "trust_score", 0.0),
                "accumulated_rewards": getattr(
                    latest_decoded_datum, "accumulated_rewards", 0
                ),
                "last_update_slot": getattr(
                    latest_decoded_datum, "last_update_slot", 0
                ),
                "performance_history_hash": getattr(
                    latest_decoded_datum, "performance_history_hash", b""
                ).hex()
                or None,
                "wallet_addr_hash": getattr(
                    latest_decoded_datum, "wallet_addr_hash", b""
                ).hex()
                or None,  # Allow None
                "status": getattr(latest_decoded_datum, "status", -1),
                "registration_slot": getattr(
                    latest_decoded_datum, "registration_slot", 0
                ),
                "api_endpoint": getattr(
                    latest_decoded_datum, "api_endpoint", b""
                ).decode("utf-8", errors="replace")
                or None,
            }
            latest_data_list.append((latest_utxo, datum_dict))
        except Exception as e:
            logger.warning(
                f"Failed to process latest MinerDatum for UID {uid_hex} from UTxO {latest_utxo.input}: {e}"
            )
            logger.debug(f"Problematic latest MinerDatum: {latest_decoded_datum}")

    if not latest_data_list:
        logger.warning(
            f"No valid latest MinerDatum UTxOs found for any UID at address {contract_address}."
        )

    logger.info(f"Processed {len(latest_data_list)} latest MinerDatum entries.")
    return latest_data_list


# --- Hàm lấy dữ liệu cho Validators ---
async def get_all_validator_data_old(
    context: BlockFrostChainContext, script_hash: ScriptHash, network: Network
) -> List[Tuple[UTxO, Dict[str, Any]]]:
    """
    [DEPRECATED] Old Cardano implementation, DO NOT USE for Aptos.
    
    Lấy và decode tất cả dữ liệu ValidatorDatum từ các UTXO tại địa chỉ script.
    CHỈ trả về dữ liệu từ UTXO mới nhất cho mỗi UID.
    """
    latest_data_list: List[Tuple[UTxO, Dict[str, Any]]] = []
    utxos_by_uid: DefaultDict[str, List[Tuple[UTxO, ValidatorData]]] = defaultdict(
        list
    )  # Nhóm theo UID
    contract_address = Address(payment_part=script_hash, network=network)
    logger.info(f"Fetching Validator UTxOs from address: {contract_address}")

    try:
        utxos: List[UTxO] = context.utxos(str(contract_address))
        logger.info(
            f"Found {len(utxos)} potential UTxOs at validator contract address."
        )
    except Exception as e:
        logger.exception(f"Failed to fetch UTxOs for address {contract_address}: {e}")
        return []

    # 1. Decode và nhóm tất cả UTXO hợp lệ theo UID
    for utxo in utxos:
        if utxo.output.datum and utxo.output.datum.cbor:  # type: ignore[attr-defined]
            try:
                # Decode bằng phương thức của lớp ValidatorDatum
                decoded_datum: ValidatorData = ValidatorData.from_cbor(  # type: ignore[assignment]
                    utxo.output.datum.cbor  # type: ignore[attr-defined]
                )

                uid_bytes = getattr(decoded_datum, "uid", None)
                if uid_bytes and isinstance(uid_bytes, bytes):
                    uid_hex = uid_bytes.hex()
                    utxos_by_uid[uid_hex].append((utxo, decoded_datum))
                else:
                    logger.warning(
                        f"Skipping UTxO {utxo.input} due to invalid or missing UID in decoded ValidatorDatum."
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to decode ValidatorDatum for UTxO {utxo.input}: {e}"
                )
                logger.debug(f"Datum CBOR: {utxo.output.datum.cbor.hex()}")  # type: ignore[attr-defined]
                continue
        elif utxo.output.datum_hash:
            logger.debug(f"Skipping UTxO {utxo.input} with datum hash.")

    # 2. Lọc và chọn UTXO mới nhất cho mỗi UID (giả định cái cuối trong list là mới nhất)
    for uid_hex, utxo_datum_list in utxos_by_uid.items():
        if not utxo_datum_list:
            continue

        # Chọn cái cuối cùng trong list, giả định nó là mới nhất
        latest_utxo, latest_decoded_datum = utxo_datum_list[-1]

        try:
            # Trích xuất thông tin từ datum mới nhất đã decode
            datum_dict = {
                "uid": uid_hex,
                "subnet_uid": getattr(latest_decoded_datum, "subnet_uid", -1),
                "stake": getattr(latest_decoded_datum, "stake", 0),
                "last_performance": getattr(
                    latest_decoded_datum, "last_performance", 0.0
                ),
                "trust_score": getattr(latest_decoded_datum, "trust_score", 0.0),
                "accumulated_rewards": getattr(
                    latest_decoded_datum, "accumulated_rewards", 0
                ),
                "last_update_slot": getattr(
                    latest_decoded_datum, "last_update_slot", 0
                ),
                "performance_history_hash": getattr(
                    latest_decoded_datum, "performance_history_hash", b""
                ).hex()
                or None,
                "wallet_addr_hash": getattr(
                    latest_decoded_datum, "wallet_addr_hash", b""
                ).hex()
                or None,  # Allow None
                "status": getattr(latest_decoded_datum, "status", -1),
                "registration_slot": getattr(
                    latest_decoded_datum, "registration_slot", 0
                ),
                "api_endpoint": getattr(
                    latest_decoded_datum, "api_endpoint", b""
                ).decode("utf-8", errors="replace")
                or None,
            }
            latest_data_list.append((latest_utxo, datum_dict))
        except Exception as e:
            logger.warning(
                f"Failed to process latest ValidatorDatum for UID {uid_hex} from UTxO {latest_utxo.input}: {e}"
            )
            logger.debug(f"Problematic latest ValidatorDatum: {latest_decoded_datum}")

    if not latest_data_list:
        logger.warning(
            f"No valid latest ValidatorDatum UTxOs found for any UID at address {contract_address}."
        )

    logger.info(f"Processed {len(latest_data_list)} latest ValidatorDatum entries.")
    return latest_data_list


# --- Có thể thêm các hàm tương tự cho SubnetDatum nếu cần ---
# async def get_all_subnet_dynamic_data(...) -> List[Dict[str, Any]]: ...
# async def get_subnet_static_data(...) -> Optional[Dict[str, Any]]: ...
