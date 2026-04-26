from streaming.kafka_utils import create_consumer

print("Creating consumer for predictions topic...")
consumer = create_consumer("predictions", "localhost:9092", "test-group", auto_offset_reset="earliest")

print("Waiting for messages...")
count = 0
for msg in consumer:
    count += 1
    print(f"Message {count}: {msg.value.get('flow_id', 'unknown')} - {msg.value.get('prediction', 'unknown')}")
    if count >= 10:
        break

print(f"Total messages received: {count}")
