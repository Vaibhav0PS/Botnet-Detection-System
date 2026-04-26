# Unsupervised Network Monitoring and Botnet Detection

Hybrid botnet detection tool for offline PCAP analysis and real-time streaming monitoring. The project reads packet captures, converts TCP/UDP traffic into 5-tuple network flows, extracts statistical flow features, and labels each source host as `Benign` or `Botnet` using pre-trained models.

## Key Features

1.  **Offline Analysis**: High-speed PCAP processing using Scapy and ML models.
2.  **Streaming Dashboard**: Real-time monitoring using Kafka, FastAPI, and React.
3.  **Live Packet Monitoring**: Sampled raw traffic view independent of the detection pipeline.
4.  **Hybrid Prediction**: Combines KMeans clustering with a Random Forest classifier.
5.  **Automated Retraining**: Fixed pipeline for regenerating models on custom datasets.

## Quick Start

### 1. Offline Detection
Processes a PCAP file and generates `result.txt` (host-level) and `flows_preprocessed_with_prediction.csv` (flow-level).

```bash
python botnetdetect.py Sample_Testing/zeus1-117.10.28.pcap
```

### 2. Launching the Dashboard (One Command)
Make sure Docker is running, then use the convenience script:

**On Windows (PowerShell):**
```powershell
.\launch_dashboard.ps1
```

**On Linux/Git Bash:**
```bash
./launch.sh
```

The system will start Kafka, the Backend API (port 8000), the Detection Consumer, and the Vite Dashboard.

## Project Structure

```text
.
├── botnetdetect.py                 # Main entry point for offline detection
├── launch_dashboard.ps1            # One-click system launcher (Windows)
├── launch.sh                       # One-click system launcher (Bash)
├── prepare_dataset.py              # Fixed: Merges CSVs with proper headers and labels
├── retrain_models.py               # Fixed: Retrains 10-cluster KMeans and RF models
├── detector/                       # Core detection and extraction logic
│   ├── feature_extractor.py        # PCAP to Flow feature conversion
│   ├── predictor.py                # Hybrid ML prediction (KMeans + RF)
│   └── host_aggregator.py          # Percentage-based host classification
├── backend/                        # FastAPI + SQLite Backend
├── consumer/                       # Kafka Prediction Consumer
├── producer/                       # PCAP Replay Producer (Kafka)
├── dashboard/                      # React (Vite) Frontend
└── Models/                         # ML Model Artifacts (scaler, encoder, cluster, rf)
```

## Dashboard Features

- **Overview Tab**: Displays high-level stats, flow counts, botnet host tracking, and threat distribution charts.
- **Live Packets Tab**: A dedicated Wireshark-style view showing sampled raw packet metadata (Time, Source, Destination, Protocol, Length) arriving in real-time.
- **Upload PCAP**: Upload any `.pcap` or `.pcapng` file directly through the UI to trigger a streaming analysis.
- **Clear Data**: Resets the SQLite database and clears all charts/tables.

## Retraining the Models

If you wish to retrain the models on the included dataset or your own:

1.  Place your raw flow CSVs in `Training_files/preprocessed_csv/benign/` or `/botnet/`.
2.  **Generate the dataset**:
    ```bash
    python prepare_dataset.py
    ```
3.  **Train the models**:
    ```bash
    python retrain_models.py
    ```
4.  **Deploy**: Copy the files from `Training_files/Models/` to the root `Models/` directory to start using them.

## Requirements

The project requires:
- Python 3.x
- Docker (for Kafka)
- Node.js (for Dashboard)
- Scapy, Pandas, Scikit-Learn, Joblib, FastAPI, Uvicorn, Kafka-Python

Install Python dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-streaming.txt
```

## Notes

- **Threshold**: A host is labeled `Botnet` if $\ge 5\%$ of its analyzed flows are predicted as malicious.
- **Protocol Support**: Currently supports IPv4 TCP and UDP traffic.
- **Environment**: The project includes a `botnet_env` virtual environment. For fresh installations, ensure `python-multipart` is installed for the upload feature.
