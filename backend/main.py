import os
import sys
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
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
    print(f"[BACKEND] Starting up using Python: {sys.executable}")
    if os.getenv("ENABLE_KAFKA_LISTENER", "1") == "1":
        print("[BACKEND] Starting Kafka listeners...")
        from backend.kafka_listener import start_kafka_listeners

        start_kafka_listeners(
            os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            os.getenv("PREDICTIONS_TOPIC", "predictions"),
            os.getenv("ALERTS_TOPIC", "alerts"),
            DB_PATH,
        )
        print("[BACKEND] Kafka listeners started")


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


@app.get("/api/packets")
def packets(limit: int = 100):
    return rows(conn, "SELECT * FROM packets ORDER BY id DESC LIMIT ?", (limit,))


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


@app.post("/api/upload-pcap")
async def upload_pcap(file: UploadFile = File(...)):
    """
    Upload a PCAP file and trigger analysis pipeline
    """
    # Validate file extension
    if not file.filename.endswith(('.pcap', '.pcapng')):
        raise HTTPException(status_code=400, detail="Only .pcap and .pcapng files are allowed")
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    file_path = upload_dir / file.filename
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Trigger producer to replay the PCAP
    try:
        result = subprocess.run(
            [sys.executable, "-m", "producer.pcap_replay_producer", str(file_path), "--replay-delay", "0.3"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Producer failed: {result.stderr}")
        
        # Extract flow count from output
        output = result.stdout.strip()
        
        return {
            "success": True,
            "message": output,
            "filename": file.filename,
            "file_path": str(file_path)
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="PCAP processing timed out (max 5 minutes)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PCAP: {str(e)}")


@app.post("/api/sync-database")
def sync_database():
    """
    Manually trigger database sync from Kafka
    """
    try:
        result = subprocess.run(
            [sys.executable, "quick_sync.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": True,
            "output": result.stdout,
            "message": "Database sync completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.delete("/api/clear-data")
def clear_data():
    """
    Clear all data from the database
    """
    try:
        conn.execute("DELETE FROM flows")
        conn.execute("DELETE FROM hosts")
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM packets")
        conn.commit()
        
        return {
            "success": True,
            "message": "All data cleared from database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")
