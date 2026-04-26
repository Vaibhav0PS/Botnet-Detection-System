"""
Quick analysis script to check uploaded PCAP results
"""
import sqlite3
from pathlib import Path

def analyze_database():
    db_path = Path("backend/botnet_stream.db")
    
    if not db_path.exists():
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 70)
    print("UPLOAD ANALYSIS REPORT")
    print("=" * 70)
    
    # Overall statistics
    print("\n📊 OVERALL STATISTICS:")
    print("-" * 70)
    
    summary = conn.execute("""
        SELECT 
            COUNT(*) as total_flows,
            SUM(CASE WHEN prediction = 'Benign' THEN 1 ELSE 0 END) as benign,
            SUM(CASE WHEN prediction = 'Botnet' THEN 1 ELSE 0 END) as botnet
        FROM flows
    """).fetchone()
    
    total = summary['total_flows']
    benign = summary['benign']
    botnet = summary['botnet']
    
    print(f"Total Flows:  {total}")
    print(f"Benign:       {benign} ({benign/total*100:.1f}%)")
    print(f"Botnet:       {botnet} ({botnet/total*100:.1f}%)")
    
    # Host statistics
    print("\n🖥️  HOST STATISTICS:")
    print("-" * 70)
    
    hosts = conn.execute("""
        SELECT 
            COUNT(*) as total_hosts,
            SUM(CASE WHEN status = 'Botnet' THEN 1 ELSE 0 END) as botnet_hosts
        FROM hosts
    """).fetchone()
    
    print(f"Total Hosts:  {hosts['total_hosts']}")
    print(f"Botnet Hosts: {hosts['botnet_hosts']}")
    
    # Top suspicious hosts
    print("\n⚠️  TOP 10 SUSPICIOUS HOSTS:")
    print("-" * 70)
    print(f"{'IP Address':<20} {'Total':<8} {'Botnet':<8} {'%':<8} {'Status'}")
    print("-" * 70)
    
    top_hosts = conn.execute("""
        SELECT src_ip, total_flows, botnet_flows, botnet_percentage, status
        FROM hosts
        ORDER BY botnet_percentage DESC, botnet_flows DESC
        LIMIT 10
    """).fetchall()
    
    for host in top_hosts:
        print(f"{host['src_ip']:<20} {host['total_flows']:<8} {host['botnet_flows']:<8} "
              f"{host['botnet_percentage']:<7.1f}% {host['status']}")
    
    # Protocol distribution
    print("\n📡 PROTOCOL DISTRIBUTION:")
    print("-" * 70)
    
    protocols = conn.execute("""
        SELECT protocol, COUNT(*) as count,
               SUM(CASE WHEN prediction = 'Botnet' THEN 1 ELSE 0 END) as botnet_count
        FROM flows
        GROUP BY protocol
        ORDER BY count DESC
    """).fetchall()
    
    for proto in protocols:
        botnet_pct = proto['botnet_count'] / proto['count'] * 100
        print(f"{proto['protocol']:<10} {proto['count']:<8} flows  "
              f"({proto['botnet_count']} botnet, {botnet_pct:.1f}%)")
    
    # Recent alerts
    print("\n🚨 RECENT ALERTS:")
    print("-" * 70)
    
    alerts = conn.execute("""
        SELECT timestamp, src_ip, botnet_percentage, reason
        FROM alerts
        ORDER BY timestamp DESC
        LIMIT 5
    """).fetchall()
    
    if alerts:
        for alert in alerts:
            print(f"[{alert['timestamp'][11:19]}] {alert['src_ip']} - "
                  f"{alert['botnet_percentage']:.1f}% - {alert['reason']}")
    else:
        print("No alerts generated")
    
    # Sample botnet flows
    print("\n🔴 SAMPLE BOTNET FLOWS:")
    print("-" * 70)
    
    botnet_flows = conn.execute("""
        SELECT src_ip, dst_ip, protocol, sport, dport
        FROM flows
        WHERE prediction = 'Botnet'
        LIMIT 5
    """).fetchall()
    
    if botnet_flows:
        print(f"{'Source':<20} {'Destination':<20} {'Proto':<8} {'Sport':<8} {'Dport'}")
        print("-" * 70)
        for flow in botnet_flows:
            print(f"{flow['src_ip']:<20} {flow['dst_ip']:<20} {flow['protocol']:<8} "
                  f"{flow['sport']:<8} {flow['dport']}")
    else:
        print("No botnet flows detected")
    
    print("\n" + "=" * 70)
    
    conn.close()

if __name__ == "__main__":
    analyze_database()
