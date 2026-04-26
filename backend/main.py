import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import DB_PATH, get_connection, init_db, rows


app = FastAPI(title="Botnet Streaming Dashboard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = get_connection(DB_PATH)
init_db(conn)


@app.on_event("startup")
def startup():
    if os.getenv("ENABLE_KAFKA_LISTENER", "1") == "1":
        from backend.kafka_listener import start_kafka_listeners

        start_kafka_listeners(
            os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            os.getenv("PREDICTIONS_TOPIC", "predictions"),
            os.getenv("ALERTS_TOPIC", "alerts"),
            DB_PATH,
        )


@app.get("/api/summary")
def summary():
    flow_counts = rows(
        conn,
        """
        SELECT
            COUNT(*) AS total_flows,
            SUM(CASE WHEN prediction = 'Benign' THEN 1 ELSE 0 END) AS benign_flows,
            SUM(CASE WHEN prediction = 'Botnet' THEN 1 ELSE 0 END) AS botnet_flows
        FROM flows
        """,
    )[0]
    host_counts = rows(
        conn,
        """
        SELECT
            COUNT(*) AS total_hosts,
            SUM(CASE WHEN status = 'Botnet' THEN 1 ELSE 0 END) AS botnet_hosts
        FROM hosts
        """,
    )[0]
    alert_counts = rows(conn, "SELECT COUNT(*) AS active_alerts FROM alerts")[0]
    return {**flow_counts, **host_counts, **alert_counts}


@app.get("/api/hosts")
def hosts(limit: int = 100):
    return rows(
        conn,
        """
        SELECT * FROM hosts
        ORDER BY status DESC, botnet_percentage DESC, last_seen DESC
        LIMIT ?
        """,
        (limit,),
    )


@app.get("/api/flows")
def flows(limit: int = 100):
    return rows(conn, "SELECT * FROM flows ORDER BY id DESC LIMIT ?", (limit,))


@app.get("/api/alerts")
def alerts(limit: int = 50):
    return rows(conn, "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))


@app.get("/api/timeseries")
def timeseries():
    return rows(
        conn,
        """
        SELECT substr(timestamp, 1, 19) AS time,
            COUNT(*) AS total,
            SUM(CASE WHEN prediction = 'Botnet' THEN 1 ELSE 0 END) AS botnet,
            SUM(CASE WHEN prediction = 'Benign' THEN 1 ELSE 0 END) AS benign
        FROM flows
        GROUP BY substr(timestamp, 1, 19)
        ORDER BY time DESC
        LIMIT 60
        """,
    )[::-1]


@app.get("/api/protocols")
def protocols():
    return rows(
        conn,
        "SELECT protocol, COUNT(*) AS count FROM flows GROUP BY protocol ORDER BY count DESC",
    )
