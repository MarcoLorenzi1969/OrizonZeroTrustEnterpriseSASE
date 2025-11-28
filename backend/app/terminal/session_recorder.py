"""
Orizon Zero Trust Connect - Session Recorder
Full audit recording of terminal sessions to MongoDB

For: Marco @ Syneto/Orizon
"""

import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase


class SessionRecorder:
    """
    Records complete terminal sessions for audit compliance.
    All input/output is timestamped and stored in MongoDB.
    """

    def __init__(
        self,
        mongodb: AsyncIOMotorDatabase,
        node_id: str,
        user_id: str,
        user_email: str,
        client_ip: str,
        user_agent: Optional[str] = None,
    ):
        self.mongodb = mongodb
        self.session_id = str(uuid.uuid4())
        self.node_id = node_id
        self.user_id = user_id
        self.user_email = user_email
        self.client_ip = client_ip
        self.user_agent = user_agent

        # Session timing
        self.started_at = datetime.utcnow()
        self.start_time = time.time()

        # Terminal size
        self.terminal_size = {"cols": 80, "rows": 24}

        # Recording buffer
        self.recording: List[Dict[str, Any]] = []

        # Stats
        self.total_input_bytes = 0
        self.total_output_bytes = 0

        # Collection name
        self.collection_name = "terminal_sessions"

    async def initialize(self):
        """Create initial session record in MongoDB."""
        try:
            session_doc = {
                "session_id": self.session_id,
                "node_id": self.node_id,
                "user_id": self.user_id,
                "user_email": self.user_email,
                "started_at": self.started_at,
                "ended_at": None,
                "duration_seconds": None,
                "client_ip": self.client_ip,
                "user_agent": self.user_agent,
                "terminal_size": self.terminal_size,
                "recording": [],
                "total_input_bytes": 0,
                "total_output_bytes": 0,
                "status": "active"
            }

            await self.mongodb[self.collection_name].insert_one(session_doc)
            logger.info(f"Terminal session started: {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to initialize session recording: {e}")

    async def record_input(self, data: str):
        """Record user input with timestamp."""
        try:
            elapsed = time.time() - self.start_time
            self.recording.append({
                "ts": round(elapsed, 3),
                "type": "input",
                "data": data
            })
            self.total_input_bytes += len(data.encode('utf-8'))

            # Batch update every 10 events
            if len(self.recording) % 10 == 0:
                await self._flush_recording()

        except Exception as e:
            logger.error(f"Failed to record input: {e}")

    async def record_output(self, data: str):
        """Record terminal output with timestamp."""
        try:
            elapsed = time.time() - self.start_time
            self.recording.append({
                "ts": round(elapsed, 3),
                "type": "output",
                "data": data
            })
            self.total_output_bytes += len(data.encode('utf-8'))

            # Batch update every 50 output events
            if len(self.recording) % 50 == 0:
                await self._flush_recording()

        except Exception as e:
            logger.error(f"Failed to record output: {e}")

    async def record_resize(self, cols: int, rows: int):
        """Record terminal resize event."""
        try:
            self.terminal_size = {"cols": cols, "rows": rows}
            elapsed = time.time() - self.start_time
            self.recording.append({
                "ts": round(elapsed, 3),
                "type": "resize",
                "cols": cols,
                "rows": rows
            })

        except Exception as e:
            logger.error(f"Failed to record resize: {e}")

    async def _flush_recording(self):
        """Flush recording buffer to MongoDB."""
        if not self.recording:
            return

        try:
            await self.mongodb[self.collection_name].update_one(
                {"session_id": self.session_id},
                {
                    "$push": {"recording": {"$each": self.recording}},
                    "$set": {
                        "total_input_bytes": self.total_input_bytes,
                        "total_output_bytes": self.total_output_bytes,
                        "terminal_size": self.terminal_size
                    }
                }
            )
            self.recording = []

        except Exception as e:
            logger.error(f"Failed to flush recording: {e}")

    async def finalize(self):
        """Finalize and close the session recording."""
        try:
            # Flush remaining recording
            await self._flush_recording()

            # Calculate duration
            ended_at = datetime.utcnow()
            duration = time.time() - self.start_time

            # Update session with final data
            await self.mongodb[self.collection_name].update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "ended_at": ended_at,
                        "duration_seconds": round(duration, 2),
                        "total_input_bytes": self.total_input_bytes,
                        "total_output_bytes": self.total_output_bytes,
                        "status": "completed"
                    }
                }
            )

            logger.info(
                f"Terminal session ended: {self.session_id} "
                f"(duration: {round(duration, 1)}s, "
                f"input: {self.total_input_bytes}b, "
                f"output: {self.total_output_bytes}b)"
            )

        except Exception as e:
            logger.error(f"Failed to finalize session: {e}")

    async def mark_error(self, error_message: str):
        """Mark session as ended with error."""
        try:
            await self._flush_recording()

            ended_at = datetime.utcnow()
            duration = time.time() - self.start_time

            await self.mongodb[self.collection_name].update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "ended_at": ended_at,
                        "duration_seconds": round(duration, 2),
                        "status": "error",
                        "error_message": error_message
                    }
                }
            )

            logger.warning(f"Terminal session error: {self.session_id} - {error_message}")

        except Exception as e:
            logger.error(f"Failed to mark session error: {e}")


class SessionManager:
    """
    Manages active terminal sessions with rate limiting.
    """

    def __init__(self, mongodb: AsyncIOMotorDatabase, redis_client=None):
        self.mongodb = mongodb
        self.redis = redis_client
        self.active_sessions: Dict[str, SessionRecorder] = {}

        # Limits
        self.max_sessions_per_user = 5
        self.max_sessions_per_node = 10

    async def can_create_session(self, user_id: str, node_id: str) -> tuple[bool, str]:
        """Check if a new session can be created (rate limiting)."""
        try:
            # Count active sessions for user
            user_sessions = await self.mongodb["terminal_sessions"].count_documents({
                "user_id": user_id,
                "status": "active"
            })

            if user_sessions >= self.max_sessions_per_user:
                return False, f"Maximum sessions per user ({self.max_sessions_per_user}) reached"

            # Count active sessions for node
            node_sessions = await self.mongodb["terminal_sessions"].count_documents({
                "node_id": node_id,
                "status": "active"
            })

            if node_sessions >= self.max_sessions_per_node:
                return False, f"Maximum sessions per node ({self.max_sessions_per_node}) reached"

            return True, ""

        except Exception as e:
            logger.error(f"Session limit check failed: {e}")
            return True, ""  # Allow on error

    def register_session(self, recorder: SessionRecorder):
        """Register an active session."""
        self.active_sessions[recorder.session_id] = recorder

    def unregister_session(self, session_id: str):
        """Unregister a session."""
        self.active_sessions.pop(session_id, None)

    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)


async def get_session_history(
    mongodb: AsyncIOMotorDatabase,
    node_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve session history for audit."""
    query = {}

    if node_id:
        query["node_id"] = node_id
    if user_id:
        query["user_id"] = user_id

    cursor = mongodb["terminal_sessions"].find(
        query,
        {
            "recording": 0  # Exclude full recording for list view
        }
    ).sort("started_at", -1).skip(offset).limit(limit)

    return await cursor.to_list(length=limit)


async def get_session_recording(
    mongodb: AsyncIOMotorDatabase,
    session_id: str
) -> Optional[Dict[str, Any]]:
    """Retrieve full session recording for playback."""
    return await mongodb["terminal_sessions"].find_one(
        {"session_id": session_id}
    )
