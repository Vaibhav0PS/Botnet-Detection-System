# Unsupervised Network Monitoring and Botnet Detection

Hybrid botnet detection tool for offline PCAP analysis. The project reads packet captures, converts TCP/UDP traffic into 5-tuple network flows, extracts statistical flow features, and labels each source host as `Benign` or `Botnet` using the pre-trained models in `Models/`.

## What the Tool Does

1. Reads a `.pcap` file with Scapy.
2. Groups packets into flows by:
   - source IP
   - destination IP
   - source port
   - destination port
   - protocol
3. Extracts flow-level features such as packet counts, payload statistics, inter-arrival times, packet-size variance, duration, and packets per second.
4. Cleans and normalizes the extracted features.
5. Predicts each flow using a hybrid approach:
   - KMeans cluster rules for obvious benign/botnet-like clusters.
   - Random Forest fallback classifier for remaining flows.
6. Aggregates flow predictions per source IP.
7. Writes host-level and flow-level results.

## Quick Start

Install the Python dependencies, then run:

```bash
python botnetdetect.py Sample_Testing/zeus1-117.10.28.pcap
```

You can also pass any absolute or relative PCAP path:

```bash
python botnetdetect.py path/to/capture.pcap
```

## Output Files

Running `botnetdetect.py` creates or refreshes these files in the project root:

- `result.txt`: host-level classification for each source IP.
- `flows_preprocessed_with_prediction.csv`: flow-level features with predicted labels.

Example `result.txt` format:

```text
10.0.2.15 , Botnet
186.18.3.72 , Benign
```

The current host decision rule labels a source IP as `Botnet` when at least 5% of its analyzed flows are predicted as botnet traffic. Otherwise, it is labeled `Benign`.

## Optional Streaming Dashboard

The project also includes an additive real-time style pipeline. It does not replace the existing `botnetdetect.py` workflow.

Install the optional Python dependencies:

```bash
pip install -r requirements-streaming.txt
```

Start Kafka:

```bash
docker compose up -d
```

In separate terminals, run the detector consumer, backend API, PCAP replay producer, and dashboard:

```bash
python -m consumer.detection_consumer
uvicorn backend.main:app --reload
python -m producer.pcap_replay_producer Sample_Testing/Botnet.pcap
cd dashboard/frontend-app
npm install
npm run dev
```

The backend exposes dashboard data at `http://localhost:8000/api/summary`, and the Vite dashboard runs at the URL printed by `npm run dev`.

## Project Structure

```text
.
├── botnetdetect.py                 # Main PCAP analysis and prediction script
├── evaluate_model.py               # Evaluation report and confusion matrix from generated predictions
├── prepare_dataset.py              # Combines preprocessed CSV files into training_dataset.csv
├── retrain_models.py               # Retrains KMeans and Random Forest artifacts from training_dataset.csv
├── train_model.py                  # Simple Random Forest retraining helper
├── plot_correlation.py             # Correlation heatmap for generated flow features
├── plot_kmeans.py                  # PCA + KMeans visualization for generated flow features
├── training_dataset.csv            # Combined training data
├── Models/
│   ├── cluster.pkl                 # KMeans model used by botnetdetect.py
│   ├── flow_predictor.joblib        # Flow classifier used by botnetdetect.py
│   ├── label_encoder.pkl           # Protocol encoder
│   └── mms.pkl                     # MinMaxScaler for flow features
├── Sample_Testing/                 # Example PCAP files
└── Training_files/
    ├── parser.py                   # Parser for Ethernet PCAP training data
    ├── parser1.py                  # Parser variant for Linux cooked captures
    ├── model.py                    # Legacy model training/evaluation workflow
    ├── preprocessed_csv/           # Expected source folder for prepared CSV files
    └── Models/                     # Alternate training output location
```

## Main Scripts

### `botnetdetect.py`

The main executable script. It accepts a PCAP path as the first command-line argument, extracts flows, loads models from `Models/`, writes per-flow predictions to `flows_preprocessed_with_prediction.csv`, and writes per-host decisions to `result.txt`.

```bash
python botnetdetect.py Sample_Testing/Botnet.pcap
```

### `evaluate_model.py`

Loads `flows_preprocessed_with_prediction.csv`, maps labels to numeric values, runs the saved flow classifier, prints a confusion matrix and classification report, and displays a confusion-matrix plot.

```bash
python evaluate_model.py
```

### `plot_correlation.py`

Creates a correlation heatmap from the numeric columns in `flows_preprocessed_with_prediction.csv`.

```bash
python plot_correlation.py
```

### `plot_kmeans.py`

Projects generated flow features to two PCA components, runs KMeans on the projection, and displays a clustering plot.

```bash
python plot_kmeans.py
```

### `prepare_dataset.py`

Combines CSV files from `Training_files/preprocessed_csv/**/*.csv` into `training_dataset.csv`.

```bash
python prepare_dataset.py
```

### `retrain_models.py`

Retrains a KMeans model, Random Forest model, label encoder, and scaler from `training_dataset.csv`. This script currently saves its artifacts under `Training_files/Models/`.

```bash
python retrain_models.py
```

If you want `botnetdetect.py` to use newly retrained artifacts, copy or save the retrained files into the root `Models/` directory with these names:

- `cluster.pkl`
- `flow_predictor.joblib`
- `label_encoder.pkl`
- `mms.pkl`

## Requirements

The project uses:

- Python 3.x
- numpy
- pandas
- scikit-learn
- scipy
- scapy
- matplotlib
- seaborn
- joblib
- natsort

Install the dependencies with:

```bash
pip install numpy pandas scikit-learn scipy scapy matplotlib seaborn joblib natsort
```

The repository also contains a local `botnet_env/` virtual environment. For a fresh setup, creating a new virtual environment is usually cleaner than relying on a copied environment.

## Dataset and Training Notes

The detection pipeline expects preprocessed flow CSV files with the same feature layout used by the included models. Training parsers in `Training_files/` were written for a dataset layout similar to:

```text
Training_files/
└── Botnet_Detection_Dataset/
    └── Botnet/
        ├── torrent/
        └── storm/
```

The parser scripts generate flow feature CSVs from PCAP directories. `prepare_dataset.py` then merges preprocessed CSV files into `training_dataset.csv`, and `retrain_models.py` can create updated model artifacts.

## Feature Summary

For each flow, the tool computes features including:

- total packets
- null packets
- small packet count and percentage
- flow duration
- average payload
- packet length standard deviation
- most frequent packet length ratio
- payload per second
- average and median inter-arrival time
- packet-size variance
- maximum packet size
- average packet length
- first packet length
- average packets per second

During preprocessing, IP address columns are removed from model input, protocol is label-encoded, selected send/receive-only timing features are dropped, and remaining numeric values are scaled with the saved MinMaxScaler.

## Notes and Assumptions

- Only IPv4 TCP and UDP traffic is analyzed.
- Flows with source ports at or below `1000` and flows with `2` or fewer packets are filtered out before prediction.
- `result.txt` contains one host-level label per source IP seen in the processed capture.
- `flows_preprocessed_with_prediction.csv` contains detailed flow-level predictions and is useful for debugging, reporting, and visualization.
- Model pickle/joblib files can be sensitive to scikit-learn version changes. `botnetdetect.py` includes compatibility fallbacks for older saved scaler/KMeans artifacts and a cluster-only fallback if the flow classifier cannot be loaded.
