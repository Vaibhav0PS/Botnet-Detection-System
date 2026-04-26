"""
Standalone script to consume Kafka messages and populate the database.
Run this separately from the FastAPI backend.
"""
from backend.database import get_connection, init_db, insert_prediction, insert_alert, DB_PATH
from streaming.kafka_utils import create_consumer

def main():
    print("[DB POPULATOR] Starting...")
    conn = get_connection(DB_PATH)
    init_db(conn)
    
    predictions_consumer = create_consumer(
        "predictions",
        "localhost:9092",
        "db-populator-predictions",
        auto_offset_reset="earliest"
    )
    
    alerts_consumer = create_consumer(
        "alerts",
        "localhost:9092",
        "db-populator-alerts",
        auto_offset_reset="earliest"
    )
    
    print("[DB POPULATOR] Consuming predictions...")
    pred_count = 0
    for msg in predictions_consumer:
        pred_count += 1
        insert_prediction(conn, msg.value)
        print(f"[DB POPULATOR] Inserted prediction {pred_count}: {msg.value.get('flow_id', 'unknown')}")
        
        # Check for alerts too
        alerts_consumer.poll(timeout_ms=0)
        for alert_msg in alerts_consumer:
            insert_alert(conn, alert_msg.value)
            print(f"[DB POPULATOR] Inserted alert: {alert_msg.value.get('src_ip', 'unknown')}")
        
        if pred_count % 10 == 0:
            print(f"[DB POPULATOR] Progress: {pred_count} predictions inserted")

if __name__ == "__main__":
    main()
