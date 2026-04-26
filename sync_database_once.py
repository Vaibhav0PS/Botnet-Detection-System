"""
One-time sync of Kafka messages to database.
"""
from backend.database import get_connection, init_db, insert_prediction, insert_alert, DB_PATH
from streaming.kafka_utils import create_consumer
import time

def main():
    print("[SYNC] Starting one-time database sync...")
    conn = get_connection(DB_PATH)
    init_db(conn)
    
    # Consume predictions
    print("[SYNC] Reading predictions from Kafka...")
    predictions_consumer = create_consumer(
        "predictions",
        "localhost:9092",
        f"sync-predictions-{int(time.time())}",  # Unique group ID
        auto_offset_reset="earliest"
    )
    
    pred_count = 0
    start_time = time.time()
    timeout = 5  # seconds
    
    try:
        while time.time() - start_time < timeout:
            msg_batch = predictions_consumer.poll(timeout_ms=1000, max_records=100)
            if not msg_batch:
                break
            
            for topic_partition, messages in msg_batch.items():
                for msg in messages:
                    pred_count += 1
                    insert_prediction(conn, msg.value)
                    if pred_count % 10 == 0:
                        print(f"[SYNC] Inserted {pred_count} predictions...")
    except Exception as e:
        print(f"[SYNC] Error: {e}")
    
    print(f"[SYNC] Total predictions inserted: {pred_count}")
    
    # Consume alerts
    print("[SYNC] Reading alerts from Kafka...")
    alerts_consumer = create_consumer(
        "alerts",
        "localhost:9092",
        f"sync-alerts-{int(time.time())}",  # Unique group ID
        auto_offset_reset="earliest"
    )
    
    alert_count = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            msg_batch = alerts_consumer.poll(timeout_ms=1000, max_records=100)
            if not msg_batch:
                break
            
            for topic_partition, messages in msg_batch.items():
                for msg in messages:
                    alert_count += 1
                    insert_alert(conn, msg.value)
    except Exception as e:
        print(f"[SYNC] Error: {e}")
    
    print(f"[SYNC] Total alerts inserted: {alert_count}")
    print("[SYNC] Sync complete!")
    
    predictions_consumer.close()
    alerts_consumer.close()

if __name__ == "__main__":
    main()
