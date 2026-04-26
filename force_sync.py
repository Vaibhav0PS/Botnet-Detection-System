"""Force sync by reading messages one at a time"""
from backend.database import get_connection, init_db, insert_prediction, DB_PATH
from kafka import KafkaConsumer
import json
import time

conn = get_connection(DB_PATH)
init_db(conn)

consumer = KafkaConsumer(
    "predictions",
    bootstrap_servers="localhost:9092",
    group_id=f"force-{int(time.time())}",
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    consumer_timeout_ms=5000,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

print("Reading predictions...")
count = 0
try:
    for msg in consumer:
        insert_prediction(conn, msg.value)
        count += 1
        if count % 50 == 0:
            print(f"  {count} predictions...")
except StopIteration:
    pass
except Exception as e:
    print(f"Stopped at {count}: {e}")

print(f"\n✓ Total: {count} predictions inserted")
consumer.close()
