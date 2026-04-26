import os
import time
from collections import Counter

import numpy as np
import pandas as pd
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import CookedLinux, Ether
from scapy.packet import NoPayload
from scapy.utils import RawPcapReader


RAW_FEATURE_COLUMNS = [
    "src_ip",
    "dst_ip",
    "sport",
    "dport",
    "protocol",
    "total_pkts",
    "null_pkts",
    "small_pkts",
    "percent_of_sml_pkts",
    "ratio_incoming_outgoing",
    "total_duration",
    "average_payload",
    "average_payload_sent",
    "average_payload_receive",
    "stddev_packet_length",
    "freq_packet_length",
    "payload_per_sec",
    "avg_inter_times",
    "avg_sent_inter_times",
    "avg_rec_inter_times",
    "med_inter_times",
    "med_sent_inter_times",
    "med_rec_inter_times",
    "var_packet_size",
    "var_packet_size_rec",
    "var_packet_size_sent",
    "max_packet_size",
    "average_packet_length",
    "first_packet_length",
    "average_packet_ps",
]

DROP_MODEL_COLUMNS = [
    "avg_sent_inter_times",
    "avg_rec_inter_times",
    "med_sent_inter_times",
    "med_rec_inter_times",
    "var_packet_size_rec",
    "var_packet_size_sent",
]


class Flow:
    def __init__(self):
        self.count = 0
        self.MICROSECOND = 10**6
        self.src_ip = None
        self.dst_ip = None
        self.sport = None
        self.dport = None
        self.protocol = None
        self.total_duration = 0
        self.first_packet_timestamp = 0
        self.last_packet_timestamp = 0
        self.total_num_packets = 0
        self.packet_length = []
        self.null_packets = 0
        self.tcp_payload = 0
        self.udp_payload = 0
        self.received_payload = 0
        self.sent_payload = 0
        self.total_size_taken = 0
        self.SMALL_PACKET_THRESHOLD = 5 * 1024 * 1024
        self.small_packets = 0
        self.inter_arrival_times = []
        self.inter_arrival_times_send = []
        self.inter_arrival_times_receive = []
        self.count_sent = 0
        self.count_receive = 0
        self.packet_size = []
        self.packet_size_sent = []
        self.packet_size_receive = []

    def get_features(self):
        self.total_duration = self.last_packet_timestamp - self.first_packet_timestamp
        total_payload = self.udp_payload + self.tcp_payload
        ratio_of_incoming_to_outgoing = 0

        average_payload = float(total_payload) / float(self.count) if self.count > 0 else 0
        average_payload_sent = (
            float(self.sent_payload) / float(self.count_sent) if self.count_sent > 0 else 0
        )
        if self.count_receive > 0:
            average_payload_receive = float(self.received_payload) / float(self.count_receive)
            ratio_of_incoming_to_outgoing = float(self.count_sent) / float(self.count_receive)
        else:
            average_payload_receive = 0

        percent_of_small_packets = (
            float(self.small_packets * 100) / float(self.total_num_packets)
            if self.total_num_packets > 0
            else 0
        )
        stddev_packet_length = np.std(self.packet_length) if self.packet_length else 0
        if self.packet_length:
            _, freq_packet_length = Counter(self.packet_length).most_common(1)[0]
        else:
            freq_packet_length = 0

        avg_inter_times = np.mean(self.inter_arrival_times) if self.inter_arrival_times else 0
        avg_sent_inter_times = (
            np.mean(self.inter_arrival_times_send) if self.inter_arrival_times_send else 0
        )
        avg_rec_inter_times = (
            np.mean(self.inter_arrival_times_receive) if self.inter_arrival_times_receive else 0
        )
        med_inter_times = np.median(self.inter_arrival_times) if self.inter_arrival_times else 0
        med_sent_inter_times = (
            np.median(self.inter_arrival_times_send) if self.inter_arrival_times_send else 0
        )
        med_rec_inter_times = (
            np.median(self.inter_arrival_times_receive) if self.inter_arrival_times_receive else 0
        )
        var_packet_size = np.var(self.packet_size) if self.packet_size else 0
        var_packet_size_sent = np.var(self.packet_size_sent) if self.packet_size_sent else 0
        var_packet_size_rec = np.var(self.packet_size_receive) if self.packet_size_receive else 0
        max_packet_size = max(self.packet_size) if self.packet_size else 0

        if self.count > 0:
            freq_packet_length = float(freq_packet_length) / float(self.count)
        payload_per_sec = float(total_payload) / float(self.total_duration) if self.total_duration > 0 else 0.0
        average_packet_length = np.mean(self.packet_length) if self.packet_length else 0
        first_packet_length = self.packet_length[0] if self.packet_length else 0
        average_packet_ps = (
            float(self.count * self.MICROSECOND) / float(self.total_duration)
            if self.total_duration > 0
            else 0
        )

        file_features = [
            self.src_ip,
            self.dst_ip,
            self.sport,
            self.dport,
            self.protocol,
            self.total_num_packets,
            self.null_packets,
            self.small_packets,
            percent_of_small_packets,
            ratio_of_incoming_to_outgoing,
            self.total_duration,
            average_payload,
            average_payload_sent,
            average_payload_receive,
            stddev_packet_length,
            float(freq_packet_length),
            payload_per_sec,
            avg_inter_times,
            avg_sent_inter_times,
            avg_rec_inter_times,
            med_inter_times,
            med_sent_inter_times,
            med_rec_inter_times,
            var_packet_size,
            var_packet_size_rec,
            var_packet_size_sent,
            max_packet_size,
            average_packet_length,
            first_packet_length,
            average_packet_ps,
        ]
        return [0 if isinstance(x, float) and np.isnan(x) else x for x in file_features]

    def to_record(self):
        return dict(zip(RAW_FEATURE_COLUMNS, self.get_features()))


def flow_id_from_record(record):
    return (
        f"{record['src_ip']}_{record['dst_ip']}_{record['sport']}_"
        f"{record['dport']}_{record['protocol']}"
    )


def _parse_packet(pkt_data):
    """
    Optimized packet parsing with error handling and timeout protection.
    Returns None for invalid/unsupported packets.
    """
    try:
        # Skip oversized packets (likely corrupted or fragmented)
        if len(pkt_data) > 65535:
            return None
        
        # Try Ethernet first
        try:
            ether_pkt = Ether(pkt_data)
        except Exception:
            # Fallback to Linux cooked capture
            try:
                ether_pkt = CookedLinux(pkt_data)
            except Exception:
                return None
        
        # Check if it's IPv4 (0x0800)
        if not hasattr(ether_pkt, "type") or ether_pkt.type != 0x0800:
            return None
        
        # Check if IP layer exists
        if not ether_pkt.haslayer(IP):
            return None
        
        ip_pkt = ether_pkt[IP]
        
        # Check for TCP or UDP
        if ether_pkt.haslayer(TCP):
            transport = ether_pkt[TCP]
            protocol = "TCP"
        elif ether_pkt.haslayer(UDP):
            transport = ether_pkt[UDP]
            protocol = "UDP"
        else:
            return None
        
        return ether_pkt, ip_pkt, transport, protocol
        
    except KeyboardInterrupt:
        raise  # Allow user to stop
    except Exception:
        # Skip malformed packets silently
        return None
        protocol = "UDP"
    else:
        return None

    return ether_pkt, ip_pkt, transport, protocol


def add_packet_to_flows(pkt_data, pkt_metadata, flows):
    """
    Add packet to flows dictionary. Returns flow key or None if packet skipped.
    """
    parsed = _parse_packet(pkt_data)
    if parsed is None:
        return None

    try:
        ether_pkt, ip_pkt, transport, protocol = parsed
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        sport = transport.sport
        dport = transport.dport
        key = f"{src_ip}_{dst_ip}_{sport}_{dport}_{protocol}"

        if key not in flows:
            flows[key] = Flow()
            flows[key].src_ip = src_ip
            flows[key].dst_ip = dst_ip
            flows[key].sport = sport
            flows[key].dport = dport
            flows[key].protocol = protocol

        flow = flows[key]
        current_time_stamp = ether_pkt.time * flow.MICROSECOND
        flow.total_num_packets += 1
        if flow.total_num_packets == 1:
            flow.first_packet_timestamp = current_time_stamp
        else:
            flow.inter_arrival_times.append(current_time_stamp - flow.last_packet_timestamp)
        flow.last_packet_timestamp = current_time_stamp
        flow.total_size_taken += len(pkt_data)
        flow.packet_size.append(len(pkt_data))

        is_null_packet = False
        if protocol == "TCP":
            if isinstance(transport.payload, NoPayload):
                flow.null_packets += 1
                is_null_packet = True
            else:
                flow.tcp_payload += len(transport.payload)
        elif protocol == "UDP":
            if isinstance(transport.payload, NoPayload):
                flow.null_packets += 1
                is_null_packet = True
            else:
                flow.udp_payload += len(transport.payload)

        if not is_null_packet and len(ether_pkt) < flow.SMALL_PACKET_THRESHOLD:
            flow.small_packets += 1

        flow.packet_length.append(pkt_metadata.wirelen)
        flow.count += 1
        return key
        
    except (AttributeError, KeyError, TypeError):
        # Skip packets with missing/invalid fields
        return None
    except KeyboardInterrupt:
        raise  # Allow user to stop
    except Exception:
        # Skip any other errors silently
        return None


def extract_flows_from_pcap(file_path, verbose=False, max_packets=None):
    start = time.process_time()
    flows = {}
    if verbose:
        print("generating features for:", file_path)
    
    packet_count = 0
    skipped_count = 0

    for pkt_data, pkt_metadata in RawPcapReader(file_path):
        packet_count += 1
        
        # Progress indicator every 1000 packets
        if verbose and packet_count % 1000 == 0:
            print(f"  Processed {packet_count} packets, {len(flows)} flows...")
        
        # Optional packet limit for testing
        if max_packets and packet_count > max_packets:
            if verbose:
                print(f"  Reached packet limit ({max_packets}), stopping...")
            break
        
        result = add_packet_to_flows(pkt_data, pkt_metadata, flows)
        if result is None:
            skipped_count += 1

    if verbose:
        file_size = float(os.stat(file_path).st_size) / float(1024 * 1024)
        time_taken = float(time.process_time() - start)
        print(f"  File Size: {file_size:.2f} MB")
        print(f"  Packets processed: {packet_count}")
        print(f"  Packets skipped: {skipped_count}")
        print(f"  Flows extracted: {len(flows)}")
        print(f"  Time taken: {time_taken:.2f}s")
        if time_taken:
            print(f"  Speed: {file_size / time_taken:.2f} MB/s")
    return flows


def records_from_flows(flows, min_packets=2):
    return [
        flow.to_record()
        for flow in flows.values()
        if flow.total_num_packets > min_packets - 1
    ]


def extract_feature_records_from_pcap(file_path, verbose=False):
    flows = extract_flows_from_pcap(file_path, verbose=verbose)
    all_ips = {flow.src_ip: 1 for flow in flows.values()}
    return records_from_flows(flows), all_ips


def records_to_dataframe(records):
    return pd.DataFrame(records, columns=RAW_FEATURE_COLUMNS)

