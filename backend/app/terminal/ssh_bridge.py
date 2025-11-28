"""
Orizon Zero Trust Connect - SSH Bridge
Bidirectional bridge between WebSocket and SSH PTY

For: Marco @ Syneto/Orizon
"""

import asyncio
import json
from typing import Optional, Callable, Awaitable
from loguru import logger
import asyncssh
from fastapi import WebSocket


class SSHBridge:
    """
    Bridges WebSocket communication with an SSH PTY session.
    Handles input/output and terminal resize events.
    """

    def __init__(
        self,
        websocket: WebSocket,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        known_hosts: Optional[str] = None,
        on_input: Optional[Callable[[str], Awaitable[None]]] = None,
        on_output: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.websocket = websocket
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.known_hosts = known_hosts
        self.on_input = on_input
        self.on_output = on_output

        self.ssh_conn: Optional[asyncssh.SSHClientConnection] = None
        self.ssh_process: Optional[asyncssh.SSHClientProcess] = None
        self._running = False
        self._tasks: list = []

        # Terminal size
        self.cols = 80
        self.rows = 24

    async def connect(self) -> bool:
        """Establish SSH connection and create PTY session."""
        try:
            # Build connection options
            connect_opts = {
                "host": self.host,
                "port": self.port,
                "username": self.username,
                "known_hosts": None,  # Skip host key verification for internal tunnels
            }

            if self.password:
                connect_opts["password"] = self.password
            elif self.private_key:
                connect_opts["client_keys"] = [self.private_key]

            logger.info(f"SSH connecting to {self.host}:{self.port} as {self.username}")

            self.ssh_conn = await asyncssh.connect(**connect_opts)

            # Create PTY process
            self.ssh_process = await self.ssh_conn.create_process(
                term_type="xterm-256color",
                term_size=(self.cols, self.rows),
            )

            logger.info(f"SSH session established to {self.host}:{self.port}")
            return True

        except asyncssh.DisconnectError as e:
            logger.error(f"SSH disconnect error: {e}")
            await self._send_error(f"SSH connection refused: {str(e)}")
            return False
        except asyncssh.PermissionDenied as e:
            logger.error(f"SSH permission denied: {e}")
            await self._send_error("SSH authentication failed")
            return False
        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            await self._send_error(f"SSH connection error: {str(e)}")
            return False

    async def start(self):
        """Start the bidirectional bridge."""
        if not self.ssh_process:
            logger.error("Cannot start bridge: SSH not connected")
            return

        self._running = True

        # Start both directions concurrently
        ws_to_ssh_task = asyncio.create_task(self._ws_to_ssh())
        ssh_to_ws_task = asyncio.create_task(self._ssh_to_ws())

        self._tasks = [ws_to_ssh_task, ssh_to_ws_task]

        # Wait for either task to complete (usually means connection closed)
        try:
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Bridge error: {e}")
        finally:
            self._running = False

    async def stop(self):
        """Stop the bridge and close connections."""
        self._running = False

        # Cancel running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Close SSH
        if self.ssh_process:
            self.ssh_process.close()
            self.ssh_process = None

        if self.ssh_conn:
            self.ssh_conn.close()
            self.ssh_conn = None

        logger.info("SSH bridge stopped")

    async def _ws_to_ssh(self):
        """Handle WebSocket to SSH direction."""
        try:
            while self._running:
                try:
                    raw_message = await asyncio.wait_for(
                        self.websocket.receive_text(),
                        timeout=60.0
                    )

                    message = json.loads(raw_message)
                    msg_type = message.get("type")

                    if msg_type == "input":
                        data = message.get("data", "")
                        if data and self.ssh_process:
                            self.ssh_process.stdin.write(data)

                            # Record input
                            if self.on_input:
                                await self.on_input(data)

                    elif msg_type == "resize":
                        cols = message.get("cols", 80)
                        rows = message.get("rows", 24)
                        await self.resize(cols, rows)

                    elif msg_type == "ping":
                        await self._send_message({"type": "pong"})

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self._send_message({"type": "ping"})
                    continue

        except Exception as e:
            if self._running:
                logger.error(f"WS to SSH error: {e}")

    async def _ssh_to_ws(self):
        """Handle SSH to WebSocket direction."""
        try:
            while self._running and self.ssh_process:
                try:
                    # Read from SSH stdout
                    data = await asyncio.wait_for(
                        self.ssh_process.stdout.read(4096),
                        timeout=0.1
                    )

                    if data:
                        await self._send_message({
                            "type": "output",
                            "data": data
                        })

                        # Record output
                        if self.on_output:
                            await self.on_output(data)

                except asyncio.TimeoutError:
                    continue
                except asyncssh.BreakReceived:
                    logger.info("SSH break received")
                    break

        except asyncssh.TerminalSizeChanged:
            # Terminal resize is handled separately
            pass
        except Exception as e:
            if self._running:
                logger.error(f"SSH to WS error: {e}")

        # SSH closed, notify client
        if self._running:
            await self._send_message({
                "type": "closed",
                "reason": "SSH session ended"
            })

    async def resize(self, cols: int, rows: int):
        """Resize the PTY terminal."""
        if self.ssh_process and (cols != self.cols or rows != self.rows):
            self.cols = cols
            self.rows = rows
            try:
                self.ssh_process.change_terminal_size(cols, rows)
                logger.debug(f"Terminal resized to {cols}x{rows}")
            except Exception as e:
                logger.error(f"Resize error: {e}")

    async def _send_message(self, message: dict):
        """Send JSON message to WebSocket."""
        try:
            await self.websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            self._running = False

    async def _send_error(self, error_message: str):
        """Send error message to WebSocket."""
        await self._send_message({
            "type": "error",
            "message": error_message
        })
