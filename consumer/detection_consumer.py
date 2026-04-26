import argparse
from datetime import datetime, timezone

from detector.feature_extractor import flow_id_from_record
from detector.host_aggregator import HostAggregator
from detector.predictor import BotnetPredictor, PRED_TO_RESULT
from streaming.kafka_utils import create_consumer, create_producer


def prediction_event_from_message(message, label):
    features = message["features"]
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "flow_id": message.get("flow_id") or flow_id_from_record(features),
        "timestamp": timestamp,
        "src_ip": features["src_ip"],
        "dst_ip": features["dst_ip"],
        "sport": int(features["sport"]),
        "dport": int(features["dport"]),
        "protocol": features["protocol"],
        "prediction": PRED_TO_RESULT[int(label)],
        "prediction_code": int(label),
    }


def run_detection_consumer(
    bootstrap_servers="localhost:9092",
    input_topic="flow_features",
    predictions_topic="predictions",
    alerts_topic="alerts",
    group_id="botnet-detector",
    models_dir="Models",
):
    print(f"[CONSUMER] Starting detection consumer...")
    print(f"[CONSUMER] Input topic: {input_topic}")
    print(f"[CONSUMER] Predictions topic: {predictions_topic}")
    print(f"[CONSUMER] Alerts topic: {alerts_topic}")
    
    predictor = BotnetPredictor(models_dir=models_dir)
    aggregator = HostAggregator()
    consumer = create_consumer(input_topic, bootstrap_servers, group_id)
    producer = create_producer(bootstrap_servers)
    
    print(f"[CONSUMER] Waiting for messages...")

    for msg in consumer:
        event = msg.value
        print(f"[CONSUMER] Received flow: {event.get('flow_id', 'unknown')}")
        records = [event["features"]]
        labels, _, _, _ = predictor.predict_records(records)
        if not labels:
            print(f"[CONSUMER] No labels generated for flow")
            continue

        prediction_event = prediction_event_from_message(event, labels[0])
        print(f"[CONSUMER] Publishing prediction: {prediction_event['prediction']} for {prediction_event['src_ip']}")
        producer.send(predictions_topic, key=prediction_event["flow_id"], value=prediction_event)

        host = aggregator.update(
            prediction_event["src_ip"],
            prediction_event["prediction"],
            timestamp=prediction_event["timestamp"],
        )
        alert = aggregator.alert_for(host)
        if alert:
            print(f"[CONSUMER] Publishing alert for {alert['src_ip']}")
            producer.send(alerts_topic, key=alert["src_ip"], value=alert)
        producer.flush()


def main():
    parser = argparse.ArgumentParser(description="Consume flow features and publish predictions.")
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--input-topic", default="flow_features")
    parser.add_argument("--predictions-topic", default="predictions")
    parser.add_argument("--alerts-topic", default="alerts")
    parser.add_argument("--group-id", default="botnet-detector")
    parser.add_argument("--models-dir", default="Models")
    args = parser.parse_args()

    run_detection_consumer(
        bootstrap_servers=args.bootstrap_servers,
        input_topic=args.input_topic,
        predictions_topic=args.predictions_topic,
        alerts_topic=args.alerts_topic,
        group_id=args.group_id,
        models_dir=args.models_dir,
    )


if __name__ == "__main__":
    main()

