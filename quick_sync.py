"""Quick database sync - Windows compatible"""
from backend.database import get_connection, init_db, insert_prediction, insert_alert, insert_packet, DB_PATH
from streaming.kafka_utils import create_consumer
import time

conn = get_connection(DB_PATH)
init_db(conn)

# Sync predictions
print("Syncing predictions...")
consumer = create_consumer("predictions", "localhost:9092", f"quick-{int(time.time())}", "earliest")
count = 0
try:
    msgs = consumer.poll(timeout_ms=5000, max_records=1000)
    for tp, messages in msgs.items():
        for msg in messages:
            insert_prediction(conn, msg.value)
            count += 1
    print(f"✓ Inserted {count} predictions")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        consumer.close()
    except:
        pass

# Sync alerts  
print("Syncing alerts...")
consumer2 = create_consumer("alerts", "localhost:9092", f"quick-alerts-{int(time.time())}", "earliest")
alert_count = 0
try:
    msgs = consumer2.poll(timeout_ms=5000, max_records=100)
    for tp, messages in msgs.items():
        for msg in messages:
            insert_alert(conn, msg.value)
            alert_count += 1
    print(f"✓ Inserted {alert_count} alerts")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        consumer2.close()
    except:
        pass

# Sync packets
print("Syncing packets...")
consumer3 = create_consumer("raw_packets", "localhost:9092", f"quick-packets-{int(time.time())}", "earliest")
packet_count = 0
try:
    msgs = consumer3.poll(timeout_ms=5000, max_records=1000)
    for tp, messages in msgs.items():
        for msg in messages:
            insert_packet(conn, msg.value)
            packet_count += 1
    print(f"✓ Inserted {packet_count} packets")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        consumer3.close()
    except:
        pass

print(f"\nDone! {count} predictions, {alert_count} alerts, {packet_count} packets")
