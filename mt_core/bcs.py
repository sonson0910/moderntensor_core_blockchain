"""
Binary Canonical Serialization (BCS) implementation for Core blockchain
Provides encoding/decoding utilities for consistent data serialization
"""

import struct
import logging
from typing import Any, List, Dict, Union, Optional
from dataclasses import dataclass, is_dataclass, fields
import json

logger = logging.getLogger(__name__)


class BCSError(Exception):
    """BCS serialization/deserialization error"""

    pass


class BCSEncoder:
    """BCS encoder for Core blockchain data structures"""

    def __init__(self):
        self.buffer = bytearray()

    def encode_bool(self, value: bool) -> "BCSEncoder":
        """Encode boolean value"""
        self.buffer.append(1 if value else 0)
        return self

    def encode_u8(self, value: int) -> "BCSEncoder":
        """Encode 8-bit unsigned integer"""
        if not (0 <= value <= 255):
            raise BCSError(f"u8 value out of range: {value}")
        self.buffer.append(value)
        return self

    def encode_u16(self, value: int) -> "BCSEncoder":
        """Encode 16-bit unsigned integer (little endian)"""
        if not (0 <= value <= 65535):
            raise BCSError(f"u16 value out of range: {value}")
        self.buffer.extend(struct.pack("<H", value))
        return self

    def encode_u32(self, value: int) -> "BCSEncoder":
        """Encode 32-bit unsigned integer (little endian)"""
        if not (0 <= value <= 4294967295):
            raise BCSError(f"u32 value out of range: {value}")
        self.buffer.extend(struct.pack("<I", value))
        return self

    def encode_u64(self, value: int) -> "BCSEncoder":
        """Encode 64-bit unsigned integer (little endian)"""
        if not (0 <= value <= 18446744073709551615):
            raise BCSError(f"u64 value out of range: {value}")
        self.buffer.extend(struct.pack("<Q", value))
        return self

    def encode_u128(self, value: int) -> "BCSEncoder":
        """Encode 128-bit unsigned integer (little endian)"""
        if not (0 <= value <= 2**128 - 1):
            raise BCSError(f"u128 value out of range: {value}")
        # Split into two 64-bit parts
        low = value & 0xFFFFFFFFFFFFFFFF
        high = (value >> 64) & 0xFFFFFFFFFFFFFFFF
        self.buffer.extend(struct.pack("<QQ", low, high))
        return self

    def encode_uleb128(self, value: int) -> "BCSEncoder":
        """Encode unsigned LEB128 (variable length encoding)"""
        if value < 0:
            raise BCSError(f"uleb128 value must be non-negative: {value}")

        while value >= 0x80:
            self.buffer.append((value & 0x7F) | 0x80)
            value >>= 7
        self.buffer.append(value & 0x7F)
        return self

    def encode_bytes(self, value: bytes) -> "BCSEncoder":
        """Encode byte array with length prefix"""
        self.encode_uleb128(len(value))
        self.buffer.extend(value)
        return self

    def encode_string(self, value: str) -> "BCSEncoder":
        """Encode UTF-8 string with length prefix"""
        encoded = value.encode("utf-8")
        return self.encode_bytes(encoded)

    def encode_option(self, value: Optional[Any], encoder_func) -> "BCSEncoder":
        """Encode optional value"""
        if value is None:
            self.encode_bool(False)
        else:
            self.encode_bool(True)
            encoder_func(value)
        return self

    def encode_vector(self, values: List[Any], encoder_func) -> "BCSEncoder":
        """Encode vector/array with length prefix"""
        self.encode_uleb128(len(values))
        for value in values:
            encoder_func(value)
        return self

    def encode_map(
        self, values: Dict[Any, Any], key_encoder, value_encoder
    ) -> "BCSEncoder":
        """Encode map/dictionary"""
        # Sort keys for canonical ordering
        sorted_items = sorted(values.items())
        self.encode_uleb128(len(sorted_items))

        for key, value in sorted_items:
            key_encoder(key)
            value_encoder(value)
        return self

    def encode_address(self, address: str) -> "BCSEncoder":
        """Encode Core blockchain address (20 bytes)"""
        # Remove 0x prefix if present
        if address.startswith("0x"):
            address = address[2:]

        # Pad to 20 bytes if needed
        if len(address) < 40:
            address = address.zfill(40)

        if len(address) != 40:
            raise BCSError(f"Invalid address length: {address}")

        try:
            addr_bytes = bytes.fromhex(address)
            self.buffer.extend(addr_bytes)
        except ValueError as e:
            raise BCSError(f"Invalid address format: {address}") from e

        return self

    def encode_struct(self, obj: Any) -> "BCSEncoder":
        """Encode dataclass or dict as struct"""
        if is_dataclass(obj):
            for field in fields(obj):
                value = getattr(obj, field.name)
                self._encode_value(value)
        elif isinstance(obj, dict):
            # Sort keys for canonical ordering
            for key in sorted(obj.keys()):
                self._encode_value(obj[key])
        else:
            raise BCSError(f"Cannot encode struct: {type(obj)}")

        return self

    def _encode_value(self, value: Any) -> "BCSEncoder":
        """Auto-encode value based on type"""
        if isinstance(value, bool):
            return self.encode_bool(value)
        elif isinstance(value, int):
            # Choose appropriate int encoding based on value
            if 0 <= value <= 255:
                return self.encode_u8(value)
            elif 0 <= value <= 65535:
                return self.encode_u16(value)
            elif 0 <= value <= 4294967295:
                return self.encode_u32(value)
            else:
                return self.encode_u64(value)
        elif isinstance(value, str):
            return self.encode_string(value)
        elif isinstance(value, bytes):
            return self.encode_bytes(value)
        elif isinstance(value, list):
            return self.encode_vector(value, self._encode_value)
        elif isinstance(value, dict):
            return self.encode_map(value, self._encode_value, self._encode_value)
        elif value is None:
            return self.encode_bool(False)  # Represent None as false
        elif is_dataclass(value):
            return self.encode_struct(value)
        else:
            raise BCSError(f"Unsupported type for encoding: {type(value)}")

    def to_bytes(self) -> bytes:
        """Get encoded bytes"""
        return bytes(self.buffer)


class BCSDecoder:
    """BCS decoder for Core blockchain data structures"""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def decode_bool(self) -> bool:
        """Decode boolean value"""
        if self.offset >= len(self.data):
            raise BCSError("Unexpected end of data while decoding bool")

        value = self.data[self.offset] != 0
        self.offset += 1
        return value

    def decode_u8(self) -> int:
        """Decode 8-bit unsigned integer"""
        if self.offset >= len(self.data):
            raise BCSError("Unexpected end of data while decoding u8")

        value = self.data[self.offset]
        self.offset += 1
        return value

    def decode_u16(self) -> int:
        """Decode 16-bit unsigned integer (little endian)"""
        if self.offset + 2 > len(self.data):
            raise BCSError("Unexpected end of data while decoding u16")

        value = struct.unpack("<H", self.data[self.offset : self.offset + 2])[0]
        self.offset += 2
        return value

    def decode_u32(self) -> int:
        """Decode 32-bit unsigned integer (little endian)"""
        if self.offset + 4 > len(self.data):
            raise BCSError("Unexpected end of data while decoding u32")

        value = struct.unpack("<I", self.data[self.offset : self.offset + 4])[0]
        self.offset += 4
        return value

    def decode_u64(self) -> int:
        """Decode 64-bit unsigned integer (little endian)"""
        if self.offset + 8 > len(self.data):
            raise BCSError("Unexpected end of data while decoding u64")

        value = struct.unpack("<Q", self.data[self.offset : self.offset + 8])[0]
        self.offset += 8
        return value

    def decode_uleb128(self) -> int:
        """Decode unsigned LEB128"""
        result = 0
        shift = 0

        while self.offset < len(self.data):
            byte = self.data[self.offset]
            self.offset += 1

            result |= (byte & 0x7F) << shift

            if (byte & 0x80) == 0:
                break

            shift += 7
            if shift >= 64:
                raise BCSError("uleb128 too large")
        else:
            raise BCSError("Unexpected end of data while decoding uleb128")

        return result

    def decode_bytes(self) -> bytes:
        """Decode byte array with length prefix"""
        length = self.decode_uleb128()

        if self.offset + length > len(self.data):
            raise BCSError("Unexpected end of data while decoding bytes")

        value = self.data[self.offset : self.offset + length]
        self.offset += length
        return value

    def decode_string(self) -> str:
        """Decode UTF-8 string with length prefix"""
        encoded = self.decode_bytes()
        try:
            return encoded.decode("utf-8")
        except UnicodeDecodeError as e:
            raise BCSError(f"Invalid UTF-8 string") from e

    def decode_address(self) -> str:
        """Decode Core blockchain address (20 bytes)"""
        if self.offset + 20 > len(self.data):
            raise BCSError("Unexpected end of data while decoding address")

        addr_bytes = self.data[self.offset : self.offset + 20]
        self.offset += 20
        return "0x" + addr_bytes.hex()

    def remaining_bytes(self) -> int:
        """Get number of remaining bytes"""
        return len(self.data) - self.offset

    def is_finished(self) -> bool:
        """Check if all data has been consumed"""
        return self.offset >= len(self.data)


# Convenience functions
def bcs_encode(obj: Any) -> bytes:
    """Encode object to BCS bytes"""
    encoder = BCSEncoder()
    encoder._encode_value(obj)
    return encoder.to_bytes()


def bcs_encode_address(address: str) -> bytes:
    """Encode address to BCS bytes"""
    encoder = BCSEncoder()
    encoder.encode_address(address)
    return encoder.to_bytes()


def bcs_encode_struct(obj: Any) -> bytes:
    """Encode struct/dataclass to BCS bytes"""
    encoder = BCSEncoder()
    encoder.encode_struct(obj)
    return encoder.to_bytes()


def bcs_decode_address(data: bytes) -> str:
    """Decode address from BCS bytes"""
    decoder = BCSDecoder(data)
    return decoder.decode_address()


# Hash function for canonical data
def canonical_hash(obj: Any) -> bytes:
    """Create canonical hash of object using BCS encoding + keccak256"""
    from eth_utils import keccak

    bcs_data = bcs_encode(obj)
    return keccak(bcs_data)


def canonical_serialize(obj: Any) -> str:
    """Serialize object to canonical hex string"""
    bcs_data = bcs_encode(obj)
    return bcs_data.hex()


@dataclass
class MinerRegistration:
    """Example struct for BCS encoding/decoding"""

    uid: str
    subnet_uid: int
    stake_amount: int
    api_endpoint: str
    owner_address: str


@dataclass
class ValidatorRegistration:
    """Example struct for BCS encoding/decoding"""

    uid: str
    subnet_uid: int
    stake_amount: int
    api_endpoint: str
    owner_address: str


@dataclass
class BitcoinStake:
    """Bitcoin staking data structure"""

    tx_hash: str
    amount: int
    lock_time: int
    owner_address: str
