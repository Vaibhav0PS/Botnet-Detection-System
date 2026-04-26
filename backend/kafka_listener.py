import threading

from backend.database import get_connection, init_db, insert_alert, insert_prediction
from streaming.kafka_utils import create_consumer


def _listen_predictions(bootstrap_servers, topic, db_path):
    conn = get_connection(db_path)
    init_db(conn)
    consumer = create_consumer(topic, bootstrap_servers, "dashboard-predictions")
    for msg in consumer:
        insert_prediction(conn, msg.value)


def _listen_alerts(bootstrap_servers, topic, db_path):
    conn = get_connection(db_path)
    init_db(conn)
    consumer = create_consumer(topic, bootstrap_servers, "dashboard-alerts")
    for msg in consumer:
        insert_alert(conn, msg.value)


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
    ]
    for thread in threads:
        thread.start()
    return threads

