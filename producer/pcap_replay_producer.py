import argparse
import time
from datetime import datetime, timezone

from scapy.layers.l2 import CookedLinux, Ether
from scapy.utils import RawPcapReader

from detector.feature_extractor import add_packet_to_flows, flow_id_from_record, records_from_flows
from streaming.kafka_utils import create_producer


def packet_timestamp(pkt_data):
    ether_pkt = Ether(pkt_data)
    if "type" not in ether_pkt.fields:
        ether_pkt = CookedLinux(pkt_data)
    return float(ether_pkt.time)


def publish_window(producer, topic, flows, window_started_at, window_ended_at):
    records = records_from_flows(flows, min_packets=2)
    for record in records:
        flow_id = flow_id_from_record(record)
        event = {
            "flow_id": flow_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pcap_window_start": window_started_at,
            "pcap_window_end": window_ended_at,
            "src_ip": record["src_ip"],
            "dst_ip": record["dst_ip"],
            "sport": int(record["sport"]),
            "dport": int(record["dport"]),
            "protocol": record["protocol"],
            "features": record,
        }
        producer.send(topic, key=flow_id, value=event)
    producer.flush()
    return len(records)


def replay_pcap(
    pcap_path,
    bootstrap_servers="localhost:9092",
    topic="flow_features",
    window_seconds=5.0,
    replay_delay=1.0,
):
    producer = create_producer(bootstrap_servers)
    flows = {}
    window_start = None
    window_end = None
    published = 0

    for pkt_data, pkt_metadata in RawPcapReader(pcap_path):
        ts = packet_timestamp(pkt_data)
        if window_start is None:
            window_start = ts
            window_end = window_start + window_seconds

        if ts >= window_end and flows:
            published += publish_window(
                producer,
                topic,
                flows,
                datetime.fromtimestamp(window_start, timezone.utc).isoformat(),
                datetime.fromtimestamp(window_end, timezone.utc).isoformat(),
            )
            flows = {}
            time.sleep(replay_delay)
            while ts >= window_end:
                window_start = window_end
                window_end = window_start + window_seconds

        add_packet_to_flows(pkt_data, pkt_metadata, flows)

    if flows and window_start is not None:
        published += publish_window(
            producer,
            topic,
            flows,
            datetime.fromtimestamp(window_start, timezone.utc).isoformat(),
            datetime.fromtimestamp(window_end, timezone.utc).isoformat(),
        )
    producer.close()
    return published


def main():
    parser = argparse.ArgumentParser(description="Replay PCAP flow features into Kafka.")
    parser.add_argument("pcap", help="Path to the PCAP file to replay")
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default="flow_features")
    parser.add_argument("--window-seconds", type=float, default=5.0)
    parser.add_argument("--replay-delay", type=float, default=1.0)
    args = parser.parse_args()

    count = replay_pcap(
        args.pcap,
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        window_seconds=args.window_seconds,
        replay_delay=args.replay_delay,
    )
    print(f"Published {count} flow feature events to {args.topic}")


if __name__ == "__main__":
    main()

