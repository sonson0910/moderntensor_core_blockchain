"""
Mock client cho Aptos API để sử dụng trong tests.
Giúp tránh gọi API thực và rate limits.
"""
import json
import random
import asyncio
import base64
from typing import Dict, List, Any, Optional, Union
from unittest.mock import AsyncMock, MagicMock
from aptos_sdk.account import Account, AccountAddress
from aptos_sdk.async_client import RestClient, ApiError, ResourceNotFound, AccountNotFound
from aptos_sdk.transactions import EntryFunction, TransactionPayload

class MockResponse:
    """Mock HTTP Response object."""
    def __init__(self, status_code: int, data: Any, headers: Optional[Dict] = None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}
    
    def json(self):
        return self._data
    
    @property
    def text(self):
        if isinstance(self._data, str):
            return self._data
        return json.dumps(self._data)

class MockHttpClient:
    """Mock HTTP client để thay thế cho RestClient.client."""
    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.default_headers = {
            "x-aptos-compute-units-remaining": "10000",
            "x-aptos-compute-units-limit": "50000"
        }
    
    async def get(self, url: str, params: Dict = None, headers: Dict = None) -> MockResponse:
        """Mock GET request."""
        # Trích xuất endpoint từ URL
        if "?" in url:
            url_parts = url.split("?")[0]
        else:
            url_parts = url
        
        # Xử lý params tùy chọn
        endpoint = url_parts.rstrip("/")
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
            if param_str:
                endpoint = f"{endpoint}?{param_str}"
        
        # Trả về response đã được cấu hình sẵn nếu có
        if endpoint in self.responses:
            response_data = self.responses[endpoint]
            if isinstance(response_data, tuple):
                status_code, data = response_data
                return MockResponse(status_code, data, self.default_headers)
            return MockResponse(200, response_data, self.default_headers)
        
        # Trả về response mặc định cho một số endpoint phổ biến
        if endpoint == "https://fullnode.testnet.aptoslabs.com/v1":
            # Root endpoint - info
            return MockResponse(200, {
                "chain_id": 2,
                "epoch": "1234",
                "ledger_version": "12345678",
                "oldest_ledger_version": "1",
                "ledger_timestamp": "1662162489123456",
                "node_role": "full_node",
                "oldest_block_height": "1",
                "block_height": "12345",
                "git_hash": "mock"
            }, self.default_headers)
        
        elif endpoint.endswith("/accounts"):
            return MockResponse(200, [], self.default_headers)
        
        elif "/accounts/" in endpoint and "/resources" in endpoint:
            # Account resources endpoint
            account_resources = [
                {
                    "type": "0x1::account::Account",
                    "data": {
                        "authentication_key": "0x1111111111111111111111111111111111111111111111111111111111111111",
                        "sequence_number": "0"
                    }
                },
                {
                    "type": "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>",
                    "data": {
                        "coin": {"value": "1000000000"},  # 10 APT
                        "frozen": False
                    }
                }
            ]
            return MockResponse(200, account_resources, self.default_headers)
        
        elif "/accounts/" in endpoint:
            # Specific account endpoint
            account_data = {
                "sequence_number": "0",
                "authentication_key": "0x1111111111111111111111111111111111111111111111111111111111111111"
            }
            return MockResponse(200, account_data, self.default_headers)
        
        elif "/transactions/" in endpoint:
            # Transaction details
            txn_data = {
                "version": "12345",
                "hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
                "state_change_hash": "0x2222222222222222222222222222222222222222222222222222222222222222",
                "event_root_hash": "0x3333333333333333333333333333333333333333333333333333333333333333",
                "state_checkpoint_hash": None,
                "gas_used": "100",
                "success": True,
                "vm_status": "Executed successfully",
                "events": [
                    {
                        "type": "0x1::aptos_account::CoinTransferEvent",
                        "data": {
                            "amount": "1000000",
                            "sender": "0x1111111111111111111111111111111111111111111111111111111111111111",
                            "receiver": "0x2222222222222222222222222222222222222222222222222222222222222222"
                        }
                    }
                ]
            }
            return MockResponse(200, txn_data, self.default_headers)
        
        # Default fallback
        return MockResponse(404, {"message": "Not found"}, self.default_headers)
    
    async def post(self, url: str, json: Dict = None, headers: Dict = None) -> MockResponse:
        """Mock POST request."""
        endpoint = url.rstrip("/")
        
        # Trả về response đã được cấu hình sẵn nếu có
        if endpoint in self.responses:
            response_data = self.responses[endpoint]
            if isinstance(response_data, tuple):
                status_code, data = response_data
                return MockResponse(status_code, data, self.default_headers)
            return MockResponse(200, response_data, self.default_headers)
        
        # Mocking các transaction submission endpoints
        if endpoint.endswith("/transactions"):
            # Giả lập gửi transaction thành công
            tx_hash = "0x" + "".join([random.choice("0123456789abcdef") for _ in range(64)])
            return MockResponse(202, {"hash": tx_hash}, self.default_headers)
        
        # View function endpoint
        if endpoint.endswith("/view"):
            # Giả lập các view function kết quả
            return MockResponse(200, ["1000000000"], self.default_headers)
        
        # Default fallback
        return MockResponse(404, {"message": "Not found"}, self.default_headers)

class MockRestClient(RestClient):
    """
    Lớp Mock cho RestClient của Aptos SDK.
    Thay thế các gọi API thực bằng mock responses.
    """
    
    def __init__(self, base_url: str = "https://fullnode.testnet.aptoslabs.com/v1", responses: Dict[str, Any] = None):
        """
        Khởi tạo MockRestClient.
        
        Args:
            base_url: URL của Aptos API (không được sử dụng nhưng giữ để tương thích)
            responses: Dictionary ánh xạ endpoint với response data
        """
        self.base_url = base_url
        self.client = MockHttpClient(responses)
        
        # Pre-configured mock data
        self._account_resources = {}
        self._account_modules = {}
    
    def configure_account_resources(self, address: str, resources: List[Dict[str, Any]]):
        """Cấu hình resources trả về cho một địa chỉ cụ thể."""
        self._account_resources[str(address)] = resources
    
    def configure_account_modules(self, address: str, modules: List[Dict[str, Any]]):
        """Cấu hình modules trả về cho một địa chỉ cụ thể."""
        self._account_modules[str(address)] = modules
    
    async def info(self) -> Dict[str, str]:
        """Trả về thông tin về node."""
        response = await self.client.get(self.base_url)
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)
        return response.json()
    
    async def chain_id(self) -> int:
        """Trả về chain ID."""
        info = await self.info()
        return int(info["chain_id"])
    
    async def account(self, account_address: AccountAddress) -> Dict[str, Any]:
        """Trả về thông tin của một tài khoản."""
        # Validate address - raise exception for invalid addresses
        if not isinstance(account_address, AccountAddress):
            try:
                if isinstance(account_address, str):
                    if not account_address.startswith("0x") or len(account_address) != 66:
                        raise AccountNotFound(f"Invalid address format: {account_address}", account_address)
            except Exception:
                raise AccountNotFound(f"Invalid address: {account_address}", account_address)
                
        response = await self.client.get(f"{self.base_url}/accounts/{account_address}")
        if response.status_code == 404:
            raise AccountNotFound(f"{account_address}", account_address)
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)
        return response.json()
    
    async def account_resources(
        self,
        account_address: AccountAddress,
        ledger_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Trả về resources của một tài khoản."""
        # Trả về custom resources nếu được cấu hình
        addr_str = str(account_address)
        if addr_str in self._account_resources:
            return self._account_resources[addr_str]
        
        response = await self.client.get(
            f"{self.base_url}/accounts/{account_address}/resources",
            params={"ledger_version": ledger_version},
        )
        if response.status_code == 404:
            raise AccountNotFound(f"{account_address}", account_address)
        if response.status_code >= 400:
            raise ApiError(f"{response.text} - {account_address}", response.status_code)
        return response.json()
    
    async def account_modules(
        self,
        account_address: AccountAddress,
        ledger_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Trả về modules của một tài khoản."""
        # Trả về custom modules nếu được cấu hình
        addr_str = str(account_address)
        if addr_str in self._account_modules:
            return self._account_modules[addr_str]
        
        # Trả về danh sách trống nếu không có cấu hình
        return []
    
    async def account_resource(
        self,
        account_address: AccountAddress,
        resource_type: str,
        ledger_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Trả về một resource cụ thể của một tài khoản."""
        resources = await self.account_resources(account_address, ledger_version)
        for resource in resources:
            if resource["type"] == resource_type:
                return resource
        raise ResourceNotFound(resource_type, account_address)
    
    async def account_sequence_number(self, account_address: AccountAddress) -> int:
        """Trả về sequence number hiện tại của tài khoản."""
        # Mô phỏng lấy sequence number
        try:
            account = await self.account(account_address)
            return int(account["sequence_number"])
        except (ApiError, ValueError, KeyError):
            # Fallback nếu có lỗi
            return 0
    
    async def simulate_transaction(
        self,
        transaction: Union[Dict[str, Any], TransactionPayload],
        sender: Union[str, AccountAddress],
        sender_account_sequence_number: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
        gas_unit_price: Optional[int] = None,
        expiration_timestamp_secs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Mô phỏng một transaction."""
        # Mô phỏng transaction thành công
        return {
            "success": True,
            "gas_used": 100,
            "vm_status": "Executed successfully",
            "changes": []
        }
    
    async def submit_transaction(self, transaction: Dict[str, Any]) -> str:
        """Gửi transaction đã ký."""
        response = await self.client.post(f"{self.base_url}/transactions", json=transaction)
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)
        return response.json()["hash"]
    
    async def submit_bcs_transaction(self, signed_transaction: bytes) -> str:
        """Gửi transaction dạng BCS."""
        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}
        tx_hex = "0x" + base64.b16encode(signed_transaction).decode('ascii').lower()
        
        # Trả về TX hash giả
        return "0x" + "".join([random.choice("0123456789abcdef") for _ in range(64)])
    
    async def wait_for_transaction(self, txn_hash: str) -> Dict[str, Any]:
        """Đợi transaction được confirm trên blockchain."""
        # Mô phỏng chờ giao dịch hoàn thành - trả về ngay lập tức
        response = await self.client.get(f"{self.base_url}/transactions/by_hash/{txn_hash}")
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)
        return response.json()
    
    async def bcs_transfer(
        self,
        sender: Account,
        recipient: AccountAddress,
        amount: int,
        sequence_number: Optional[int] = None,
        max_gas_amount: Optional[int] = None,
        gas_unit_price: Optional[int] = None,
        expiration_timestamp_secs: Optional[int] = None,
    ) -> str:
        """Thực hiện chuyển token bằng BCS."""
        # Mô phỏng giao dịch chuyển token thành công
        tx_hash = "0x" + "".join([random.choice("0123456789abcdef") for _ in range(64)])
        return tx_hash 