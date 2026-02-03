"""Binary protocol encoder/decoder for Civ7 debug port communication."""

import struct
from dataclasses import dataclass
from typing import Optional


# Protocol constants
MESSAGE_TYPE = 3
CMD_PREFIX = "CMD:65535:"
HEADER_SIZE = 8  # 4 bytes length + 4 bytes type


class ProtocolError(Exception):
    """Raised when protocol encoding/decoding fails."""
    pass


@dataclass
class Message:
    """Represents a protocol message."""
    msg_type: int
    payload: str


def encode_command(javascript: str) -> bytes:
    """
    Encode a JavaScript command into the binary protocol format.

    Format:
        [4 bytes: payload length, little-endian]
        [4 bytes: message type (0x00000003), little-endian]
        [payload: CMD:65535:{javascript}\0]

    Args:
        javascript: The JavaScript code to send.

    Returns:
        The encoded binary message.

    Raises:
        ProtocolError: If encoding fails.
    """
    try:
        # Build payload with null terminator
        payload = f"{CMD_PREFIX}{javascript}\0"
        payload_bytes = payload.encode("utf-8")

        # Build header: length (4 bytes LE) + type (4 bytes LE)
        length = len(payload_bytes)
        header = struct.pack("<II", length, MESSAGE_TYPE)

        return header + payload_bytes
    except Exception as e:
        raise ProtocolError(f"Failed to encode command: {e}") from e


def decode_header(data: bytes) -> tuple[int, int]:
    """
    Decode the 8-byte header from received data.

    Args:
        data: The 8-byte header data.

    Returns:
        Tuple of (payload_length, message_type).

    Raises:
        ProtocolError: If header is invalid.
    """
    if len(data) < HEADER_SIZE:
        raise ProtocolError(f"Header too short: expected {HEADER_SIZE} bytes, got {len(data)}")

    try:
        length, msg_type = struct.unpack("<II", data[:HEADER_SIZE])
        return length, msg_type
    except struct.error as e:
        raise ProtocolError(f"Failed to decode header: {e}") from e


def decode_payload(data: bytes) -> str:
    """
    Decode the payload bytes into a string.

    Args:
        data: The payload bytes (may include null terminator).

    Returns:
        The decoded string without null terminator.

    Raises:
        ProtocolError: If decoding fails.
    """
    try:
        # Strip null terminator if present
        if data and data[-1:] == b'\0':
            data = data[:-1]
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ProtocolError(f"Failed to decode payload: {e}") from e


def decode_message(header: bytes, payload: bytes) -> Message:
    """
    Decode a complete message from header and payload bytes.

    Args:
        header: The 8-byte header.
        payload: The payload bytes.

    Returns:
        A Message object containing the decoded data.

    Raises:
        ProtocolError: If decoding fails.
    """
    length, msg_type = decode_header(header)

    if len(payload) != length:
        raise ProtocolError(f"Payload length mismatch: expected {length}, got {len(payload)}")

    payload_str = decode_payload(payload)
    return Message(msg_type=msg_type, payload=payload_str)
