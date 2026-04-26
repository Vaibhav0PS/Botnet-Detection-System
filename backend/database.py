import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "botnet_stream.db"


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id TEXT,
            timestamp TEXT,
            src_ip TEXT,
            dst_ip TEXT,
            sport INTEGER,
            dport INTEGER,
            protocol TEXT,
            prediction TEXT
        );

        CREATE TABLE IF NOT EXISTS hosts (
            src_ip TEXT PRIMARY KEY,
            total_flows INTEGER NOT NULL,
            benign_flows INTEGER NOT NULL,
            botnet_flows INTEGER NOT NULL,
            botnet_percentage REAL NOT NULL,
            status TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            src_ip TEXT,
            status TEXT,
            botnet_percentage REAL,
            reason TEXT
        );

        CREATE TABLE IF NOT EXISTS packets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            src_ip TEXT,
            dst_ip TEXT,
            protocol TEXT,
            length INTEGER,
            info TEXT
        );
        """
    )
    conn.commit()


def rows(conn, query, params=()):
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def one(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def insert_packet(conn, event):
    conn.execute(
        """
        INSERT INTO packets (timestamp, src_ip, dst_ip, protocol, length, info)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event["timestamp"],
            event["src_ip"],
            event["dst_ip"],
            event["protocol"],
            event["length"],
            event["info"],
        ),
    )
    conn.commit()


def insert_prediction(conn, event):
    conn.execute(
        """
        INSERT INTO flows
        (flow_id, timestamp, src_ip, dst_ip, sport, dport, protocol, prediction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["flow_id"],
            event["timestamp"],
            event["src_ip"],
            event["dst_ip"],
            event["sport"],
            event["dport"],
            event["protocol"],
            event["prediction"],
        ),
    )
    update_host_from_prediction(conn, event)
    conn.commit()


def update_host_from_prediction(conn, event):
    host = one(conn, "SELECT * FROM hosts WHERE src_ip = ?", (event["src_ip"],))
    if host is None:
        host = {
            "src_ip": event["src_ip"],
            "total_flows": 0,
            "benign_flows": 0,
            "botnet_flows": 0,
            "botnet_percentage": 0.0,
            "status": "Benign",
            "last_seen": event["timestamp"],
        }

    host["total_flows"] += 1
    if event["prediction"] == "Botnet":
        host["botnet_flows"] += 1
    else:
        host["benign_flows"] += 1
    host["botnet_percentage"] = host["botnet_flows"] * 100.0 / host["total_flows"]
    host["status"] = "Botnet" if host["botnet_percentage"] >= 5.0 else "Benign"
    host["last_seen"] = event["timestamp"]

    conn.execute(
        """
        INSERT INTO hosts
        (src_ip, total_flows, benign_flows, botnet_flows, botnet_percentage, status, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(src_ip) DO UPDATE SET
            total_flows=excluded.total_flows,
            benign_flows=excluded.benign_flows,
            botnet_flows=excluded.botnet_flows,
            botnet_percentage=excluded.botnet_percentage,
            status=excluded.status,
            last_seen=excluded.last_seen
        """,
        (
            host["src_ip"],
            host["total_flows"],
            host["benign_flows"],
            host["botnet_flows"],
            host["botnet_percentage"],
            host["status"],
            host["last_seen"],
        ),
    )


def insert_alert(conn, event):
    conn.execute(
        """
        INSERT INTO alerts (timestamp, src_ip, status, botnet_percentage, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            event["timestamp"],
            event["src_ip"],
            event["status"],
            event["botnet_percentage"],
            event["reason"],
        ),
    )
    conn.commit()

