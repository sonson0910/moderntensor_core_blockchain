# file: cardano_service.py

import logging
from typing import List, Optional
from pycardano import (
    BlockFrostChainContext,
    Network,
    Address,
    TransactionBuilder,
    TransactionOutput,
    AssetClass,
    MultiAsset,
    Value,
    PaymentSigningKey,
    Transaction,
    TransactionWitnessSet,
    TransactionBody,
    UTxO,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CardanoService:
    """
    Dịch vụ tương tác Cardano, ví dụ qua BlockFrost.
    Hỗ trợ:
      - get_address_info: lấy UTxO/số dư
      - send_ada: gửi ADA
      - send_token: gửi native token
    """

    def __init__(
        self,
        project_id: str,
        network: Network = Network.TESTNET,
    ):
        """
        :param project_id: Blockfrost project ID
        :param network: Mạng Cardano (MAINNET, TESTNET), default TESTNET
        """
        self.project_id = project_id
        self.network = network

        # Tạo chain context qua BlockFrost
        self.chain_context = BlockFrostChainContext(
            project_id=self.project_id,
            base_url=(
                "https://cardano-preprod.blockfrost.io/api/v0"
                if network == Network.TESTNET
                else "https://cardano-mainnet.blockfrost.io/api/v0"
            ),
        )

    def get_address_info(self, address_str: str) -> dict:
        """
        Lấy thông tin cơ bản về địa chỉ Cardano: UTxO, số dư,...
        """
        address = Address.from_primitive(address_str)
        utxos = self.chain_context.utxos(address)  # list[UTxO]

        # Tính tổng ADA
        total_lovelace = 0
        # Tính native token
        token_balances = {}  # { (policy_id, asset_name): quantity }

        for utxo in utxos:
            val: Value = utxo.output.amount
            # val.coin là số lovelace
            total_lovelace += val.coin
            # val.multi_asset là dict-like
            if val.multi_asset:
                for policy, assets in val.multi_asset.items():
                    for asset_name, amount in assets.items():
                        key = (policy, asset_name)
                        token_balances[key] = token_balances.get(key, 0) + amount

        return {
            "address": address_str,
            "lovelace": total_lovelace,
            "tokens": token_balances,
            "utxo_count": len(utxos),
        }

    def send_ada(
        self,
        from_signing_key: PaymentSigningKey,
        to_address_str: str,
        lovelace_amount: int,
        change_address_str: Optional[str] = None,
    ) -> str:
        """
        Gửi ADA (lovelace) từ 'from_signing_key' đến 'to_address_str'.
        :param from_signing_key: private key (payment signing key) đại diện hotkey
        :param to_address_str: địa chỉ đích
        :param lovelace_amount: số lovelace (1 ADA = 1_000_000 lovelace)
        :param change_address_str: địa chỉ thối (mặc định = địa chỉ gốc)
        :return: transaction id
        """
        # Address nguồn
        from_address = Address(
            payment_part=from_signing_key.to_public_key().hash(),
            network=self.network
        )
        # Địa chỉ đích
        to_address = Address.from_primitive(to_address_str)

        if not change_address_str:
            change_address = from_address
        else:
            change_address = Address.from_primitive(change_address_str)

        # Khởi tạo builder
        builder = TransactionBuilder(self.chain_context)

        # Lấy UTxO từ from_address
        utxos = self.chain_context.utxos(from_address)

        # Add input
        for utxo in utxos:
            builder.add_input(utxo)

        # Add output: Gửi lovelace
        builder.add_output(TransactionOutput(to_address, lovelace_amount))

        # Build transaction (auto-calc fee, change)
        tx_body = builder.build(change_address=change_address)
        tx_id = self.sign_and_submit(tx_body, from_signing_key)
        logger.info(f"[send_ada] Sent {lovelace_amount} lovelace to {to_address_str}, tx_id={tx_id}")
        return tx_id

    def send_token(
        self,
        from_signing_key: PaymentSigningKey,
        to_address_str: str,
        policy_id: str,
        asset_name: str,
        token_amount: int,
        lovelace_amount: int = 2000000,
        change_address_str: Optional[str] = None
    ) -> str:
        """
        Gửi native token (moderntensor token, etc) từ from_signing_key -> to_address_str.
        :param policy_id: hex string (policy ID)
        :param asset_name: hex string (nếu asset name là dạng bytes), hoặc string (nếu ASCII)
        :param token_amount: số lượng token gửi
        :param lovelace_amount: ADA tối thiểu kèm output (thường ~1-2 ADA)
        """
        from_address = Address(
            payment_part=from_signing_key.to_public_key().hash(),
            network=self.network
        )
        to_address = Address.from_primitive(to_address_str)
        if not change_address_str:
            change_address = from_address
        else:
            change_address = Address.from_primitive(change_address_str)

        builder = TransactionBuilder(self.chain_context)
        utxos = self.chain_context.utxos(from_address)
        for utxo in utxos:
            builder.add_input(utxo)

        # Tạo MultiAsset
        asset_class = AssetClass(bytes.fromhex(policy_id), asset_name.encode('utf-8') if isinstance(asset_name, str) else asset_name)
        multi_asset = MultiAsset.from_assets({asset_class: token_amount})

        # Tạo giá trị output
        value = Value(lovelace_amount, multi_asset)

        builder.add_output(TransactionOutput(to_address, value))
        tx_body = builder.build(change_address=change_address)
        tx_id = self.sign_and_submit(tx_body, from_signing_key)
        logger.info(f"[send_token] Sent {token_amount} {asset_name} from policy {policy_id} to {to_address_str}, tx_id={tx_id}")
        return tx_id

    def sign_and_submit(
        self,
        tx_body: TransactionBody,
        signing_key: PaymentSigningKey
    ) -> str:
        """
        Ký transaction và submit lên chain. Trả về tx_id (hash).
        """
        # Tạo witness
        witness = TransactionWitnessSet()
        witness.signatures[signing_key.hash()] = signing_key.sign(tx_body.hash())

        tx = Transaction(tx_body, witness_set=witness)
        # Submit
        tx_id = self.chain_context.submit_tx(tx)
        return tx_id
