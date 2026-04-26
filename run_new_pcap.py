#!/usr/bin/env python3
"""
Script to run a new PCAP file and update the dashboard.
Usage: python run_new_pcap.py Sample_Testing/zeus1-117.10.28.pcap
"""
import sys
import os
import time
import subprocess
import requests

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_new_pcap.py <pcap_file>")
        print("\nAvailable PCAP files:")
        print("  - Sample_Testing/Botnet.pcap (mixed traffic)")
        print("  - Sample_Testing/zeus1-117.10.28.pcap (Zeus botnet)")
        print("  - Sample_Testing/torrent_00018_20180321111851.pcap (benign P2P)")
        return 1
    
    pcap_file = sys.argv[1]
    
    if not os.path.exists(pcap_file):
        print(f"Error: File not found: {pcap_file}")
        return 1
    
    print("=" * 60)
    print("Running New PCAP Analysis")
    print("=" * 60)
    print(f"PCAP File: {pcap_file}\n")
    
    # Step 1: Clear database
    print("[1/4] Clearing database...")
    db_path = "backend/botnet_stream.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("✓ Database cleared!\n")
        except Exception as e:
            print(f"⚠ Warning: Could not delete database: {e}")
            print("  (Backend might be running - stop it first)\n")
    
    # Step 2: Run producer
    print("[2/4] Replaying PCAP file...")
    result = subprocess.run(
        ["python", "-m", "producer.pcap_replay_producer", pcap_file, "--replay-delay", "0.3"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✓ {result.stdout.strip()}\n")
    else:
        print(f"✗ Error: {result.stderr}\n")
        return 1
    
    # Step 3: Wait for consumer
    print("[3/4] Waiting for ML predictions...")
    time.sleep(3)
    print("✓ Processing complete!\n")
    
    # Step 4: Sync database
    print("[4/4] Syncing database...")
    result = subprocess.run(
        ["python", "sync_database_once.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # Show summary
    print("=" * 60)
    print("Analysis Complete!")
    print("=" * 60)
    print("Dashboard: http://localhost:5173/\n")
    
    try:
        response = requests.get("http://localhost:8000/api/summary")
        if response.status_code == 200:
            summary = response.json()
            print("API Summary:")
            print(f"  Total Flows:  {summary.get('total_flows', 0)}")
            print(f"  Benign Flows: {summary.get('benign_flows', 0)}")
            print(f"  Botnet Flows: {summary.get('botnet_flows', 0)}")
            print(f"  Total Hosts:  {summary.get('total_hosts', 0)}")
            print(f"  Botnet Hosts: {summary.get('botnet_hosts', 0)}")
            
            if summary.get('botnet_hosts', 0) > 0:
                print(f"\n⚠ WARNING: {summary['botnet_hosts']} botnet host(s) detected!")
        else:
            print("⚠ Backend API not responding. Is it running?")
    except Exception as e:
        print(f"⚠ Could not fetch summary: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
