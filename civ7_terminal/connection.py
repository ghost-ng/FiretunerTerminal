"""Async connection manager with auto-reconnect for Civ7 debug port."""

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

from .protocol import (
    HEADER_SIZE,
    Message,
    ProtocolError,
    decode_header,
    decode_message,
    encode_command,
)


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()


@dataclass
class ConnectionConfig:
    """Connection configuration."""
    host: str = "127.0.0.1"
    port: int = 4318
    initial_retry_delay: float = 2.0
    max_retry_delay: float = 30.0
    retry_backoff_multiplier: float = 2.0


class ConnectionError(Exception):
    """Raised when connection operations fail."""
    pass


class ConnectionManager:
    """
    Manages async socket connection with auto-reconnect.

    Provides:
    - Automatic connection retry with exponential backoff
    - Command queuing during disconnect
    - State change callbacks for UI updates
    """

    def __init__(
        self,
        config: ConnectionConfig,
        on_state_change: Optional[Callable[[ConnectionState, Optional[float]], None]] = None,
        on_response: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str, bool], None]] = None,
    ):
        """
        Initialize the connection manager.

        Args:
            config: Connection configuration.
            on_state_change: Callback for state changes (state, retry_countdown).
            on_response: Callback for received responses.
            on_error: Callback for error messages.
        """
        self.config = config
        self._on_state_change = on_state_change
        self._on_response = on_response
        self._on_error = on_error

        self._state = ConnectionState.DISCONNECTED
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        self._command_queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending_responses: asyncio.Queue[asyncio.Future[str]] = asyncio.Queue()

        self._retry_delay = config.initial_retry_delay
        self._shutdown_event = asyncio.Event()
        self._connection_task: Optional[asyncio.Task] = None
        self._sender_task: Optional[asyncio.Task] = None
        self._receiver_task: Optional[asyncio.Task] = None

        # Dedup repeated error messages
        self._last_error_msg: Optional[str] = None
        self._error_count: int = 0

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._state == ConnectionState.CONNECTED

    def _set_state(self, state: ConnectionState, retry_countdown: Optional[float] = None) -> None:
        """Update state and notify callback."""
        self._state = state
        if self._on_state_change:
            self._on_state_change(state, retry_countdown)

    def _notify_error(self, message: str) -> None:
        """Notify error callback, collapsing repeated identical messages."""
        if not self._on_error:
            return

        if message == self._last_error_msg:
            self._error_count += 1
            self._on_error(f"{message} (x{self._error_count})", True)
        else:
            self._last_error_msg = message
            self._error_count = 1
            self._on_error(message, False)

    def _notify_response(self, response: str) -> None:
        """Notify response callback."""
        if self._on_response:
            self._on_response(response)

    async def start(self) -> None:
        """Start the connection manager and begin connecting."""
        if self._connection_task is not None:
            return

        self._shutdown_event.clear()
        self._connection_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        """Stop the connection manager and close connection."""
        self._shutdown_event.set()

        # Cancel all tasks
        for task in [self._sender_task, self._receiver_task, self._connection_task]:
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self._close_connection()

        self._connection_task = None
        self._sender_task = None
        self._receiver_task = None

    async def send_command(self, javascript: str) -> Optional[str]:
        """
        Send a JavaScript command and wait for response.

        Args:
            javascript: The JavaScript code to execute.

        Returns:
            The response string, or None if send failed.
        """
        if not javascript.strip():
            return None

        # Create a future for the response
        response_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()

        # Queue the command and its response future
        await self._command_queue.put(javascript)
        await self._pending_responses.put(response_future)

        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self._notify_error("Command timed out waiting for response")
            return None
        except asyncio.CancelledError:
            return None

    async def _connection_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        while not self._shutdown_event.is_set():
            try:
                await self._connect()

                if self._state == ConnectionState.CONNECTED:
                    # Reset retry delay and error dedup on successful connection
                    self._retry_delay = self.config.initial_retry_delay
                    self._last_error_msg = None
                    self._error_count = 0

                    # Start sender and receiver tasks
                    self._sender_task = asyncio.create_task(self._sender_loop())
                    self._receiver_task = asyncio.create_task(self._receiver_loop())

                    # Wait for either task to complete (indicating disconnection)
                    done, pending = await asyncio.wait(
                        [self._sender_task, self._receiver_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Cancel remaining tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                    # Check for exceptions
                    for task in done:
                        try:
                            task.result()
                        except Exception as e:
                            self._notify_error(f"Connection error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._notify_error(f"Connection failed: {e}")

            # Clean up connection
            await self._close_connection()

            if self._shutdown_event.is_set():
                break

            # Wait before retry with countdown
            await self._wait_for_retry()

    async def _connect(self) -> None:
        """Establish connection to the debug port."""
        self._set_state(ConnectionState.CONNECTING)

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=10.0,
            )
            self._set_state(ConnectionState.CONNECTED)
        except asyncio.TimeoutError:
            raise ConnectionError("Connection timed out")
        except OSError as e:
            raise ConnectionError(f"Failed to connect: {e}")

    async def _close_connection(self) -> None:
        """Close the current connection."""
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass  # Ignore errors during close
            self._writer = None
            self._reader = None

        self._set_state(ConnectionState.DISCONNECTED)

        # Fail any pending response futures
        while not self._pending_responses.empty():
            try:
                future = self._pending_responses.get_nowait()
                if not future.done():
                    future.cancel()
            except asyncio.QueueEmpty:
                break

    async def _wait_for_retry(self) -> None:
        """Wait for retry with countdown updates."""
        remaining = self._retry_delay

        while remaining > 0 and not self._shutdown_event.is_set():
            self._set_state(ConnectionState.DISCONNECTED, remaining)
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=min(1.0, remaining),
                )
                break
            except asyncio.TimeoutError:
                remaining -= 1.0

        # Increase retry delay with backoff
        self._retry_delay = min(
            self._retry_delay * self.config.retry_backoff_multiplier,
            self.config.max_retry_delay,
        )

    async def _sender_loop(self) -> None:
        """Send queued commands."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for command with timeout to allow checking shutdown
                try:
                    command = await asyncio.wait_for(
                        self._command_queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                if self._writer is None:
                    continue

                # Encode and send command
                data = encode_command(command)
                self._writer.write(data)
                await self._writer.drain()

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._notify_error(f"Send error: {e}")
                raise

    async def _receiver_loop(self) -> None:
        """Receive and process responses."""
        while not self._shutdown_event.is_set():
            try:
                if self._reader is None:
                    break

                # Read header
                header = await self._reader.readexactly(HEADER_SIZE)
                length, msg_type = decode_header(header)

                # Read payload
                payload = await self._reader.readexactly(length)
                message = decode_message(header, payload)

                # Notify response callback
                self._notify_response(message.payload)

                # Complete pending response future
                try:
                    future = self._pending_responses.get_nowait()
                    if not future.done():
                        future.set_result(message.payload)
                except asyncio.QueueEmpty:
                    pass  # Unsolicited response

            except asyncio.IncompleteReadError:
                # Connection closed
                break
            except asyncio.CancelledError:
                raise
            except ProtocolError as e:
                self._notify_error(f"Protocol error: {e}")
                raise
            except Exception as e:
                self._notify_error(f"Receive error: {e}")
                raise
