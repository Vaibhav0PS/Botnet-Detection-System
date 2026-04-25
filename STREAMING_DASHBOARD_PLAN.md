# Real-Time Botnet Detection Streaming Plan

## Goal

Build a real-time style botnet detection system that:

1. Simulates live traffic from a PCAP file.
2. Extracts flow features from that traffic.
3. Produces flow events into Kafka.
4. Consumes those flow events for ML prediction.
5. Aggregates flow predictions into host-level botnet decisions.
6. Shows the live prediction stream in a dashboard.

This approach is easier to implement than direct live packet capture and fits the current project because the existing code already works on `.pcap` files and flow-based features.

## Safety Principle

The streaming system must be built as an **additive layer** around the current project, not as a replacement for it.

That means:

- the existing `botnetdetect.py` workflow must continue to run
- the current `Models/` artifacts must stay unchanged unless intentionally replaced
- the current output files such as `result.txt` and `flows_preprocessed_with_prediction.csv` must keep working
- Kafka, FastAPI, SQLite, and the dashboard must be optional new components, not required for the old script

If any part of the streaming implementation fails, the current project should still remain usable in its original form.

## Non-Disruption Rules

To avoid affecting the current state of the project, follow these rules during implementation:

- do not remove or rewrite the current command-line behavior of `botnetdetect.py`
- do not change the feature order expected by the saved models
- do not overwrite files in `Models/` during early development
- do not make the old script depend on Kafka, the backend, or the dashboard
- do not rename existing output files used by the current workflow
- keep new streaming code in separate folders and modules

## Safe Migration Strategy

The safest way to implement this plan is:

1. Keep the current project runnable exactly as it is.
2. Extract reusable logic carefully into helper modules without breaking the old script.
3. Build the streaming pipeline in parallel as a new path.
4. Test the streaming path independently.
5. Only after the new path is stable, optionally let the old script reuse the shared helpers.

This reduces risk because the existing project remains the fallback path at every stage.

## Recommended Tech Stack

Use this stack for the easiest implementation with good project value:

- `Python`: packet parsing, feature extraction, ML prediction, Kafka clients, backend logic.
- `Scapy`: replay and parse packets from PCAP files.
- `Apache Kafka`: event streaming between producer, predictor, and dashboard backend.
- `FastAPI`: backend APIs for dashboard data and optional WebSocket streaming.
- `React`: frontend dashboard.
- `Chart.js` or `Recharts`: live charts and visualizations.
- `SQLite`: lightweight storage for predictions, host summaries, and alerts.
- `Docker Compose`: easiest way to run Kafka locally.

## Why This Stack

- `Python` matches the current codebase and model pipeline.
- `Scapy` is already used in `botnetdetect.py`.
- `Kafka` makes the architecture look and behave like a true streaming system.
- `FastAPI` is simpler than building a larger backend stack and works well for APIs.
- `React` gives enough flexibility for a live dashboard.
- `SQLite` avoids extra database setup during development.
- `Docker Compose` keeps Kafka setup manageable.

## Recommended Architecture

```text
PCAP File
   |
   v
PCAP Replay Producer
   |
   v
Kafka Topic: flow_features
   |
   v
ML Detection Consumer
   |
   +--> Kafka Topic: predictions
   |
   +--> Kafka Topic: alerts
   |
   v
FastAPI Backend + SQLite
   |
   v
React Dashboard
```

## Core Design Decision

The best option is to stream **flow features**, not raw packets.

Why:

- Raw packet streaming is harder because another service must rebuild flows and maintain packet state.
- Flow-level streaming fits the current project because feature extraction already exists.
- It is much easier to debug.
- It is still realistic enough for a real-time network monitoring demo.

So the recommended design is:

```text
Simulated PCAP replay -> Flow feature events -> Kafka -> Prediction service -> Dashboard
```

## System Components

## 1. PCAP Replay Producer

### Purpose

Simulate live traffic from a saved PCAP file.

### What it does

- Reads packets from a PCAP file using Scapy.
- Groups packets into flows using the same 5-tuple logic already used in the project:
  - source IP
  - destination IP
  - source port
  - destination port
  - protocol
- Extracts the same flow features used by the current model.
- Sends each completed or updated flow feature record to Kafka.

### Kafka topic used

- `flow_features`

### Recommended simulation behavior

Do not process the full file instantly. Instead:

- Read packets in time windows such as `5 seconds`.
- After each window, extract features from flows in that window.
- Publish those flow features to Kafka.
- Wait briefly before publishing the next window so the dashboard feels live.

### Recommended first implementation

Use a replay delay like:

- process `5 seconds` of PCAP traffic
- publish results
- sleep `1 to 2 seconds`

This gives a live-demo feel without becoming slow.

### Example event shape

```json
{
  "flow_id": "10.0.2.15_186.50.139.76_15931_21963_UDP",
  "timestamp": "2026-04-25T22:10:00",
  "src_ip": "10.0.2.15",
  "dst_ip": "186.50.139.76",
  "sport": 15931,
  "dport": 21963,
  "protocol": "UDP",
  "features": {
    "total_pkts": 9,
    "null_pkts": 0,
    "small_pkts": 9,
    "percent_of_sml_pkts": 100.0,
    "total_duration": 8901832.0,
    "average_payload": 72.0,
    "stddev_packet_length": 0.0,
    "payload_per_sec": 0.000072
  }
}
```

## 2. Kafka

### Purpose

Act as the streaming backbone between data generation, ML prediction, alerting, and the dashboard.

### Recommended topics

- `flow_features`
- `predictions`
- `alerts`

### Topic responsibilities

- `flow_features`: carries extracted flow feature events from replayed PCAP traffic.
- `predictions`: carries per-flow ML predictions.
- `alerts`: carries host-level botnet alerts.

### Why Kafka works well here

- Components stay decoupled.
- You can scale producer and consumer separately.
- The dashboard backend can consume the same prediction stream without being tightly coupled to the ML logic.
- It gives the project a strong real-time architecture story.

## 3. ML Detection Consumer

### Purpose

Read flow features from Kafka, run ML prediction, and publish prediction results.

### Input topic

- `flow_features`

### Output topics

- `predictions`
- `alerts`

### What it does

- Reads a flow feature event from Kafka.
- Converts the message into the exact model input format expected by the saved scaler and model.
- Loads:
  - `Models/mms.pkl`
  - `Models/cluster.pkl`
  - `Models/flow_predictor.joblib`
  - `Models/label_encoder.pkl`
- Applies the same preprocessing and prediction logic currently used in `botnetdetect.py`.
- Produces a predicted label for each flow.
- Maintains host-level counters per source IP.
- Publishes an alert when a source IP crosses the botnet threshold.

### Prediction output example

```json
{
  "flow_id": "10.0.2.15_186.50.139.76_15931_21963_UDP",
  "timestamp": "2026-04-25T22:10:05",
  "src_ip": "10.0.2.15",
  "dst_ip": "186.50.139.76",
  "sport": 15931,
  "dport": 21963,
  "protocol": "UDP",
  "prediction": "Botnet",
  "prediction_code": 1
}
```

## 4. Host Aggregation Logic

### Purpose

Convert per-flow predictions into per-host detection status.

### Current project rule

The current logic in `botnetdetect.py` marks a host as `Botnet` when at least `5%` of its analyzed flows are predicted as botnet traffic.

### What should be tracked per source IP

- `src_ip`
- `total_flows`
- `benign_flows`
- `botnet_flows`
- `botnet_percentage`
- `status`
- `last_seen`

### Alert output example

```json
{
  "timestamp": "2026-04-25T22:10:08",
  "src_ip": "10.0.2.15",
  "status": "Botnet",
  "botnet_percentage": 12.5,
  "reason": "Botnet flow percentage exceeded 5%"
}
```

### Simplest implementation choice

Keep this aggregation logic inside the ML consumer at first. That is easier than creating another separate stream processor too early.

## 5. FastAPI Backend

### Purpose

Provide dashboard data through APIs and optionally push live updates.

### What it does

- Consumes prediction and alert events.
- Stores those events in SQLite.
- Exposes APIs for the dashboard.
- Optionally streams updates using WebSocket.

### Recommended API endpoints

- `GET /api/summary`
- `GET /api/hosts`
- `GET /api/flows`
- `GET /api/alerts`
- `GET /api/timeseries`
- `WS /ws/predictions`

### Easiest first version

Start with normal REST endpoints and frontend polling every `2 seconds`.

### Better later version

Add WebSocket updates after the basic flow works.

## 6. SQLite Database

### Purpose

Store current and recent prediction data so the dashboard can refresh reliably.

### Why SQLite

- very easy to set up
- no separate server
- enough for a local prototype and demo
- easy to inspect during debugging

### Suggested tables

#### `flows`

- `id`
- `flow_id`
- `timestamp`
- `src_ip`
- `dst_ip`
- `sport`
- `dport`
- `protocol`
- `prediction`

#### `hosts`

- `src_ip`
- `total_flows`
- `benign_flows`
- `botnet_flows`
- `botnet_percentage`
- `status`
- `last_seen`

#### `alerts`

- `id`
- `timestamp`
- `src_ip`
- `status`
- `botnet_percentage`
- `reason`

## 7. React Dashboard

### Purpose

Show the detection pipeline as a live monitoring dashboard instead of only writing output files.

### Main dashboard sections

#### Overview cards

Show:

- total flows analyzed
- benign flows
- botnet flows
- total hosts
- botnet hosts
- active alerts

#### Live flow stream table

Columns:

- time
- source IP
- destination IP
- protocol
- source port
- destination port
- prediction

#### Host monitoring table

Columns:

- source IP
- total flows
- benign flows
- botnet flows
- botnet percentage
- status
- last seen

#### Charts

Recommended:

- benign vs botnet distribution
- flows over time
- top suspicious source IPs
- protocol distribution

#### Alerts panel

Show recent alert messages like:

```text
10.0.2.15 marked Botnet - 12.5% botnet flows
```

## Recommended Frontend Strategy

The easiest frontend path is:

- `React`
- `Recharts` or `Chart.js`
- polling every `2 seconds`

Do not start with:

- advanced state management
- WebSocket-first complexity
- too many pages

A single dashboard page is enough for the first version.

## Recommended Development Phases

## Phase 0: Protect the Current Workflow

### Goal

Preserve the current project behavior before adding any streaming features.

### Tasks

- confirm `botnetdetect.py` remains the primary existing entry point
- keep current models in `Models/` untouched
- keep existing output files and naming unchanged
- create new streaming-related code in separate modules and folders
- treat the existing script as the baseline behavior to preserve

### Result

The current project stays usable even if the new streaming pipeline is incomplete or broken.

## Phase 1: Refactor the Current Detection Logic

### Goal

Make the existing project reusable for streaming without breaking current behavior.

### Tasks

- Separate feature extraction from command-line execution.
- Separate prediction logic from CSV and text-file writing.
- Create reusable functions for:
  - packet-to-flow extraction
  - flow feature generation
  - preprocessing
  - prediction
  - host aggregation
- keep `botnetdetect.py` calling the same overall flow it uses today
- verify the old script still produces the same file outputs after refactoring

### Result

The current codebase becomes usable as a library for the replay producer and prediction consumer, while the original script still works.

## Phase 2: Set Up Kafka

### Goal

Run Kafka locally with the smallest possible setup.

### Tasks

- Use Docker Compose to run Kafka.
- Create required topics:
  - `flow_features`
  - `predictions`
  - `alerts`

### Result

The event pipeline is ready for development.

## Phase 3: Build the PCAP Replay Producer

### Goal

Simulate live traffic from saved packet captures.

### Tasks

- Read a PCAP file using Scapy.
- Process packets in replay windows.
- Build flows from packets.
- Extract the same model features used today.
- Publish flow feature events to Kafka.
- Add configurable replay delay.

### Result

Kafka begins receiving flow events as if traffic were arriving live.

## Phase 4: Build the ML Detection Consumer

### Goal

Turn flow feature events into predictions and alerts.

### Tasks

- Consume messages from `flow_features`.
- Load model artifacts from `Models/`.
- Preprocess features correctly.
- Predict flow labels.
- Update host-level counters.
- Publish:
  - flow predictions to `predictions`
  - host alerts to `alerts`

### Result

The system begins producing real-time detection outputs.

## Phase 5: Build the Backend API

### Goal

Expose the live data to the dashboard.

### Tasks

- Consume `predictions` and `alerts`.
- Store records in SQLite.
- Build FastAPI endpoints for summary tables and charts.
- Add polling support first.

### Result

Frontend can request structured live dashboard data.

## Phase 6: Build the Dashboard

### Goal

Visualize the streaming pipeline.

### Tasks

- Create summary cards.
- Create live flow table.
- Create host status table.
- Create alerts list.
- Create charts.
- Refresh the screen every `2 seconds`.

### Result

You have a usable live dashboard for the simulated streaming system.

## Phase 7: Improve the Demo Experience

### Goal

Make the system polished and presentation-ready.

### Tasks

- add play, pause, restart replay controls
- add filters by IP, protocol, or label
- show replay speed
- show latest alert timestamp
- add export for predictions or alerts

### Result

The project becomes much easier to demo and explain.

## Suggested Folder Structure

```text
project-root/
|-- botnetdetect.py
|-- detector/
|   |-- feature_extractor.py
|   |-- predictor.py
|   `-- host_aggregator.py
|-- producer/
|   `-- pcap_replay_producer.py
|-- consumer/
|   `-- detection_consumer.py
|-- backend/
|   |-- main.py
|   |-- database.py
|   `-- kafka_listener.py
|-- dashboard/
|   `-- frontend-app/
|-- Models/
|-- Sample_Testing/
|-- docker-compose.yml
`-- STREAMING_DASHBOARD_PLAN.md
```

## Implementation Priorities

If the goal is to get a working system quickly, build in this exact order:

1. Protect the current workflow and keep `botnetdetect.py` unchanged from the user point of view.
2. Refactor current detection logic into reusable modules.
3. Build Kafka setup with Docker Compose.
4. Build the PCAP replay producer.
5. Build the ML detection consumer.
6. Build FastAPI backend with SQLite.
7. Build the React dashboard.
8. Add polish such as replay controls and WebSocket updates.

## What To Avoid At First

To keep implementation manageable, avoid these in the first version:

- direct live network interface capture
- streaming every raw packet into Kafka
- PostgreSQL
- Kubernetes
- multiple backend services for tiny responsibilities
- complex authentication
- advanced distributed processing

## Best Final Build for This Project

The best balance of ease, realism, and demo value is:

```text
PCAP replay simulation
-> Kafka flow_features topic
-> ML prediction consumer
-> Kafka predictions and alerts topics
-> FastAPI + SQLite backend
-> React dashboard
```

## Final Recommendation

This architecture is the most practical path for the current project.

It is:

- easier than direct live packet capture
- aligned with the current PCAP-based code
- realistic enough to demonstrate streaming detection
- strong enough for a dashboard-driven final project
- safe to implement without breaking the current project if built as a parallel path

If needed later, this system can be extended to real live capture by replacing the PCAP replay producer with a packet-sniffing producer while keeping Kafka, prediction logic, backend, and dashboard mostly unchanged.
