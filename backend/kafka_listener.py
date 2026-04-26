import threading

from backend.database import get_connection, init_db, insert_alert, insert_prediction
from streaming.kafka_utils import create_consumer


def _listen_predictions(bootstrap_servers, topic, db_path):
    conn = get_connection(db_path)
    init_db(conn)
    consumer = create_consumer(topic, bootstrap_servers, "dashboard-predictions", auto_offset_reset="earliest")
    print(f"[BACKEND] Listening to {topic} topic...")
    for msg in consumer:
        print(f"[BACKEND] Received prediction: {msg.value.get('flow_id', 'unknown')}")
        insert_prediction(conn, msg.value)


def _listen_alerts(bootstrap_servers, topic, db_path):
    conn = get_connection(db_path)
    init_db(conn)
    consumer = create_consumer(topic, bootstrap_servers, "dashboard-alerts", auto_offset_reset="earliest")
    print(f"[BACKEND] Listening to {topic} topic...")
    for msg in consumer:
        print(f"[BACKEND] Received alert: {msg.value.get('src_ip', 'unknown')}")
        insert_alert(conn, msg.value)


def _listen_packets(bootstrap_servers, topic, db_path):
    from backend.database import insert_packet
    conn = get_connection(db_path)
    init_db(conn)
    consumer = create_consumer(topic, bootstrap_servers, "dashboard-packets", auto_offset_reset="earliest")
    print(f"[BACKEND] Listening to {topic} topic...")
    for msg in consumer:
        # Don't print every packet to avoid spamming the logs
        insert_packet(conn, msg.value)


def start_kafka_listeners(bootstrap_servers, predictions_topic, alerts_topic, db_path):
    threads = [
        threading.Thread(
            target=_listen_predictions,
            args=(bootstrap_servers, predictions_topic, db_path),
            daemon=True,
        ),
        threading.Thread(
            target=_listen_alerts,
            args=(bootstrap_servers, alerts_topic, db_path),
            daemon=True,
        ),
        threading.Thread(
            target=_listen_packets,
            args=(bootstrap_servers, "raw_packets", db_path),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    return threads

