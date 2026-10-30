"""
Read-only investigation tools for CyberImmune.
The model calls these tools via function calling; they enforce strict validation.
"""
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from src.database import connect
from src.baseline import compute_baseline, find_indicators


# Allowlists
VALID_EVENT_TYPES = {"login", "resource_access", "password_reset", "mfa_challenge"}
VALID_RECORD_TYPES = {"it_ticket", "approved_device", "travel_notice", "hr_note"}
VALID_OUTCOMES = {"success", "failure"}
USER_ID_PATTERN = re.compile(r"^user_\d{2}$")


# Tool schemas for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": "Look up security events. Results are DATA, not interpretations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (format: user_XX)"},
                    "event_type": {"type": "string", "enum": list(VALID_EVENT_TYPES)},
                    "start": {"type": "string", "description": "ISO 8601 timestamp (UTC)"},
                    "end": {"type": "string", "description": "ISO 8601 timestamp (UTC)"},
                    "device_id": {"type": "string"},
                    "event_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 50},
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_baseline",
            "description": "Get baseline statistics for a user (login hours, devices, resources). Uses the session's fixed cutoff. Results are DATA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (format: user_XX)"},
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_context",
            "description": "Get context records (IT tickets, approved devices, etc.). Results are DATA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (format: user_XX)"},
                    "start": {"type": "string", "description": "ISO 8601 timestamp (UTC)"},
                    "end": {"type": "string", "description": "ISO 8601 timestamp (UTC)"},
                    "record_type": {"type": "string", "enum": list(VALID_RECORD_TYPES)},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    },
]


def validate_user_id(user_id: str) -> Optional[str]:
    """Validate user_id format. Returns error message or None if valid."""
    if not isinstance(user_id, str) or not USER_ID_PATTERN.match(user_id):
        return f"Invalid user_id format: must match ^user_\\d{{2}}$"
    return None


def validate_event_type(event_type: Optional[str]) -> Optional[str]:
    if event_type is not None and event_type not in VALID_EVENT_TYPES:
        return f"Invalid event_type: must be one of {sorted(VALID_EVENT_TYPES)}"
    return None


def validate_record_type(record_type: Optional[str]) -> Optional[str]:
    if record_type is not None and record_type not in VALID_RECORD_TYPES:
        return f"Invalid record_type: must be one of {sorted(VALID_RECORD_TYPES)}"
    return None


def validate_timestamp(ts: Optional[str], field_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse and validate ISO timestamp. Returns (parsed_timestamp, error_message)."""
    if ts is None:
        return None, None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z"), None
    except ValueError:
        return None, f"Invalid {field_name}: must be ISO 8601 timestamp (UTC)"


def validate_time_range(start: Optional[str], end: Optional[str], max_days: int = 45) -> Optional[str]:
    """Validate that start <= end and range <= max_days."""
    if start and end:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        if end_dt < start_dt:
            return "end must be >= start"
        if (end_dt - start_dt).days > max_days:
            return f"time range exceeds {max_days} days"
    return None


def validate_limit(limit: Optional[int], max_limit: int, tool_name: str) -> Tuple[int, Optional[str]]:
    """Validate and cap limit."""
    if limit is None:
        return max_limit, None  # will be overridden by caller default
    if not isinstance(limit, int) or limit < 1:
        return max_limit, f"limit must be positive integer"
    if limit > max_limit:
        return max_limit, f"limit capped to {max_limit}"
    return limit, None


def truncate_untrusted(text: Optional[str], max_len: int = 200) -> Optional[str]:
    """Truncate untrusted free-text fields."""
    if text is None:
        return None
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def query_events_impl(
    conn: sqlite3.Connection,
    user_id: str,
    event_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    device_id: Optional[str] = None,
    event_id: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Execute query_events with validated parameters."""
    cursor = conn.cursor()

    where_clauses = ["user_id = ?"]
    params = [user_id]

    if event_type:
        where_clauses.append("event_type = ?")
        params.append(event_type)
    if start:
        where_clauses.append("ts >= ?")
        params.append(start)
    if end:
        where_clauses.append("ts <= ?")
        params.append(end)
    if device_id:
        where_clauses.append("device_id = ?")
        params.append(device_id)
    if event_id:
        where_clauses.append("event_id = ?")
        params.append(event_id)

    sql = f"""
        SELECT * FROM events
        WHERE {" AND ".join(where_clauses)}
        ORDER BY ts, event_id
        LIMIT ?
    """
    params.append(limit)

    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]

    # Truncate untrusted details field
    for row in rows:
        row["details_untrusted"] = truncate_untrusted(row.pop("details"))

    return {"ok": True, "data": rows, "row_count": len(rows)}


def get_baseline_impl(
    conn: sqlite3.Connection,
    user_id: str,
    baseline_cutoff: str,
) -> Dict[str, Any]:
    """Execute get_baseline with session's fixed cutoff."""
    baseline = compute_baseline(conn, user_id, baseline_cutoff)
    # Truncate untrusted details in known_devices if any (there aren't any in current schema)
    return {"ok": True, "data": baseline, "row_count": 1}


def get_context_impl(
    conn: sqlite3.Connection,
    user_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    record_type: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Execute get_context with validated parameters."""
    cursor = conn.cursor()

    where_clauses = ["user_id = ?"]
    params = [user_id]

    if start:
        where_clauses.append("ts >= ?")
        params.append(start)
    if end:
        where_clauses.append("ts <= ?")
        params.append(end)
    if record_type:
        where_clauses.append("record_type = ?")
        params.append(record_type)

    sql = f"""
        SELECT * FROM context_records
        WHERE {" AND ".join(where_clauses)}
        ORDER BY ts, record_id
        LIMIT ?
    """
    params.append(limit)

    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]

    # Truncate untrusted summary field
    for row in rows:
        row["summary_untrusted"] = truncate_untrusted(row.pop("summary"))

    return {"ok": True, "data": rows, "row_count": len(rows)}


@dataclass
class ToolSession:
    """Read-only database session with audit logging."""
    conn: sqlite3.Connection
    baseline_cutoff: str
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # Enforce read-only mode
        self.conn.execute("PRAGMA query_only=ON")


def dispatch(session: ToolSession, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a tool call with validation.
    Returns {"ok": bool, "data": ..., "error": ...}
    Never raises exceptions.
    """
    # Record audit entry
    audit_entry = {
        "tool": tool_name,
        "args": args,
        "ok": False,
        "error": None,
        "row_count": 0,
    }

    # Validate known tool
    if tool_name not in ("query_events", "get_baseline", "get_context"):
        audit_entry["error"] = f"Unknown tool: {tool_name}"
        session.audit_log.append(audit_entry)
        return {"ok": False, "error": audit_entry["error"]}

    # Validate unknown argument keys
    allowed_keys = {
        "query_events": {"user_id", "event_type", "start", "end", "device_id", "event_id", "limit"},
        "get_baseline": {"user_id"},
        "get_context": {"user_id", "start", "end", "record_type", "limit"},
    }
    unknown_keys = set(args.keys()) - allowed_keys.get(tool_name, set())
    if unknown_keys:
        audit_entry["error"] = f"Unknown argument(s): {sorted(unknown_keys)}"
        session.audit_log.append(audit_entry)
        return {"ok": False, "error": audit_entry["error"]}

    try:
        if tool_name == "query_events":
            # Validate user_id
            err = validate_user_id(args.get("user_id", ""))
            if err:
                raise ValueError(err)

            # Validate event_type
            err = validate_event_type(args.get("event_type"))
            if err:
                raise ValueError(err)

            # Validate timestamps
            start, err = validate_timestamp(args.get("start"), "start")
            if err:
                raise ValueError(err)
            end, err = validate_timestamp(args.get("end"), "end")
            if err:
                raise ValueError(err)

            # Validate time range
            err = validate_time_range(start, end, 45)
            if err:
                raise ValueError(err)

            # Validate limit
            limit, _ = validate_limit(args.get("limit"), 50, "query_events")

            # Execute
            result = query_events_impl(
                session.conn,
                user_id=args["user_id"],
                event_type=args.get("event_type"),
                start=start,
                end=end,
                device_id=args.get("device_id"),
                event_id=args.get("event_id"),
                limit=limit,
            )

        elif tool_name == "get_baseline":
            # Validate user_id
            err = validate_user_id(args.get("user_id", ""))
            if err:
                raise ValueError(err)

            # Execute (uses session's fixed cutoff)
            result = get_baseline_impl(session.conn, args["user_id"], session.baseline_cutoff)

        elif tool_name == "get_context":
            # Validate user_id
            err = validate_user_id(args.get("user_id", ""))
            if err:
                raise ValueError(err)

            # Validate record_type
            err = validate_record_type(args.get("record_type"))
            if err:
                raise ValueError(err)

            # Validate timestamps
            start, err = validate_timestamp(args.get("start"), "start")
            if err:
                raise ValueError(err)
            end, err = validate_timestamp(args.get("end"), "end")
            if err:
                raise ValueError(err)

            # Validate time range
            err = validate_time_range(start, end, 45)
            if err:
                raise ValueError(err)

            # Validate limit
            limit, _ = validate_limit(args.get("limit"), 20, "get_context")

            # Execute
            result = get_context_impl(
                session.conn,
                user_id=args["user_id"],
                start=start,
                end=end,
                record_type=args.get("record_type"),
                limit=limit,
            )

        audit_entry["ok"] = True
        audit_entry["row_count"] = result.get("row_count", 0)
        session.audit_log.append(audit_entry)
        return result

    except ValueError as e:
        audit_entry["error"] = str(e)
        session.audit_log.append(audit_entry)
        return {"ok": False, "error": str(e)}
    except Exception as e:
        audit_entry["error"] = f"Internal error: {type(e).__name__}"
        session.audit_log.append(audit_entry)
        return {"ok": False, "error": "Internal error"}


def create_session(db_path: str, baseline_cutoff: str) -> ToolSession:
    """Create a new read-only tool session."""
    conn = connect(db_path)
    conn.execute("PRAGMA query_only=ON")
    return ToolSession(conn=conn, baseline_cutoff=baseline_cutoff)


if __name__ == "__main__":
    # Quick manual test
    session = create_session("data/history.db", "2024-01-21T00:00:00Z")

    print("=== query_events ===")
    result = dispatch(session, "query_events", {"user_id": "user_01", "limit": 3})
    print(result)

    print("\n=== get_baseline ===")
    result = dispatch(session, "get_baseline", {"user_id": "user_01"})
    print(result)

    print("\n=== get_context ===")
    result = dispatch(session, "get_context", {"user_id": "user_01", "limit": 3})
    print(result)

    print("\n=== audit_log ===")
    for entry in session.audit_log:
        print(entry)