import argparse
import time
from datetime import datetime, timezone
from scapy.layers.inet import IP, TCP, UDP
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


RAW_PACKETS_TOPIC = "raw_packets"


def publish_packets(producer, topic, packet_metadata_list):
    print(f"[PRODUCER] Publishing {len(packet_metadata_list)} raw packets to {topic}")
    for pkt in packet_metadata_list:
        producer.send(topic, value=pkt)
    producer.flush()


def replay_pcap(
    pcap_path,
    bootstrap_servers="localhost:9092",
    topic="flow_features",
    window_seconds=5.0,
    replay_delay=1.0,
    packet_sample_rate=5,
):
    producer = create_producer(bootstrap_servers)
    flows = {}
    window_start = None
    window_end = None
    published = 0
    
    current_window_packets = []

    for pkt_data, pkt_metadata in RawPcapReader(pcap_path):
        ts = packet_timestamp(pkt_data)
        if window_start is None:
            window_start = ts
            window_end = window_start + window_seconds

        if ts >= window_end:
            if flows:
                published += publish_window(
                    producer,
                    topic,
                    flows,
                    datetime.fromtimestamp(window_start, timezone.utc).isoformat(),
                    datetime.fromtimestamp(window_end, timezone.utc).isoformat(),
                )
            
            # Also publish the sampled raw packets for this window
            if current_window_packets:
                publish_packets(producer, RAW_PACKETS_TOPIC, current_window_packets)
                current_window_packets = []
                
            flows = {}
            time.sleep(replay_delay)
            while ts >= window_end:
                window_start = window_end
                window_end = window_start + window_seconds

        # Add to flows (existing logic)
        key = add_packet_to_flows(pkt_data, pkt_metadata, flows)
        
        # Sample raw packet metadata for live monitoring
        if key and len(current_window_packets) < packet_sample_rate:
            try:
                ether_pkt = Ether(pkt_data)
                if ether_pkt.haslayer(IP):
                    ip = ether_pkt[IP]
                    proto = "OTHER"
                    if ip.haslayer(TCP): proto = "TCP"
                    elif ip.haslayer(UDP): proto = "UDP"
                    
                    packet_event = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "src_ip": ip.src,
                        "dst_ip": ip.dst,
                        "protocol": proto,
                        "length": pkt_metadata.wirelen,
                        "info": f"{proto} {ip.src} -> {ip.dst}"
                    }
                    current_window_packets.append(packet_event)
            except Exception as e:
                # print(f"Error sampling packet: {e}")
                pass

    if flows and window_start is not None:
        published += publish_window(
            producer,
            topic,
            flows,
            datetime.fromtimestamp(window_start, timezone.utc).isoformat(),
            datetime.fromtimestamp(window_end, timezone.utc).isoformat(),
        )
        if current_window_packets:
            publish_packets(producer, RAW_PACKETS_TOPIC, current_window_packets)
            
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

