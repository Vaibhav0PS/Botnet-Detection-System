from datetime import datetime, timezone

from detector.predictor import BENIGN_CLASS_NAME, BOTNET_CLASS_NAME


class HostAggregator:
    def __init__(self, threshold_percent=5.0):
        self.threshold_percent = threshold_percent
        self.hosts = {}
        self.alerted_hosts = set()

    def update(self, src_ip, prediction, timestamp=None):
        now = timestamp or datetime.now(timezone.utc).isoformat()
        host = self.hosts.setdefault(
            src_ip,
            {
                "src_ip": src_ip,
                "total_flows": 0,
                "benign_flows": 0,
                "botnet_flows": 0,
                "botnet_percentage": 0.0,
                "status": BENIGN_CLASS_NAME,
                "last_seen": now,
            },
        )
        host["total_flows"] += 1
        if prediction == BOTNET_CLASS_NAME or prediction == 1:
            host["botnet_flows"] += 1
        else:
            host["benign_flows"] += 1
        host["botnet_percentage"] = (
            host["botnet_flows"] * 100.0 / host["total_flows"] if host["total_flows"] else 0.0
        )
        host["status"] = (
            BOTNET_CLASS_NAME
            if host["botnet_percentage"] >= self.threshold_percent
            else BENIGN_CLASS_NAME
        )
        host["last_seen"] = now
        return host.copy()

    def update_many(self, src_ips, predictions):
        for src_ip, prediction in zip(src_ips, predictions):
            self.update(src_ip, prediction)
        return self.hosts

    def alert_for(self, host):
        if host["status"] != BOTNET_CLASS_NAME or host["src_ip"] in self.alerted_hosts:
            return None
        self.alerted_hosts.add(host["src_ip"])
        return {
            "timestamp": host["last_seen"],
            "src_ip": host["src_ip"],
            "status": host["status"],
            "botnet_percentage": host["botnet_percentage"],
            "reason": "Botnet flow percentage exceeded 5%",
        }


def host_status_lines(src_ips, predictions, all_ips):
    grouped = {}
    for src_ip, prediction in zip(src_ips, predictions):
        grouped.setdefault(src_ip, []).append(int(prediction))

    lines = []
    for src_ip, values in grouped.items():
        percentage = sum(values) / len(values)
        status = BENIGN_CLASS_NAME if percentage * 100 < 5 else BOTNET_CLASS_NAME
        lines.append(f"{src_ip} , {status}")

    for src_ip in all_ips:
        if src_ip not in grouped:
            lines.append(f"{src_ip} , {BENIGN_CLASS_NAME}")
    return lines
