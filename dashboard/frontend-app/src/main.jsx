import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  MonitorDot,
  ShieldCheck,
  Upload,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function usePollingData() {
  const [state, setState] = useState({
    summary: {},
    flows: [],
    hosts: [],
    alerts: [],
    timeseries: [],
    protocols: [],
    error: "",
  });

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [summary, flows, hosts, alerts, timeseries, protocols] = await Promise.all(
          [
            "/api/summary",
            "/api/flows?limit=60",
            "/api/hosts?limit=50",
            "/api/alerts?limit=20",
            "/api/timeseries",
            "/api/protocols",
          ].map((path) => fetch(`${API_BASE}${path}`).then((response) => response.json())),
        );
        if (active) {
          setState({ summary, flows, hosts, alerts, timeseries, protocols, error: "" });
        }
      } catch (error) {
        if (active) {
          setState((current) => ({ ...current, error: error.message }));
        }
      }
    }

    load();
    const timer = setInterval(load, 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return state;
}

function StatCard({ icon: Icon, label, value, tone }) {
  return (
    <section className={`stat-card ${tone}`}>
      <div className="stat-icon">
        <Icon size={20} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value ?? 0}</strong>
      </div>
    </section>
  );
}

function Badge({ value }) {
  return <span className={`badge ${value === "Botnet" ? "danger" : "safe"}`}>{value}</span>;
}

function UploadPanel() {
  const [uploading, setUploading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage("");
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/api/upload-pcap`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(data.message || "PCAP uploaded and processed successfully!");
        // Auto-sync after 2 seconds
        setTimeout(() => handleSync(), 2000);
      } else {
        setError(data.detail || "Upload failed");
      }
    } catch (err) {
      setError("Failed to upload file: " + err.message);
    } finally {
      setUploading(false);
      event.target.value = ""; // Reset file input
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setMessage("");
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/sync-database`, {
        method: "POST",
      });

      const data = await response.json();

      if (response.ok) {
        setMessage("Database synced successfully!");
      } else {
        setError(data.detail || "Sync failed");
      }
    } catch (err) {
      setError("Failed to sync: " + err.message);
    } finally {
      setSyncing(false);
    }
  };

  const handleClear = async () => {
    if (!confirm("Are you sure you want to clear all data?")) return;

    try {
      const response = await fetch(`${API_BASE}/api/clear-data`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (response.ok) {
        setMessage("All data cleared!");
      } else {
        setError(data.detail || "Clear failed");
      }
    } catch (err) {
      setError("Failed to clear data: " + err.message);
    }
  };

  return (
    <div className="upload-panel">
      <div className="upload-actions">
        <label className="upload-button">
          <Upload size={16} />
          {uploading ? "Uploading..." : "Upload PCAP"}
          <input
            type="file"
            accept=".pcap,.pcapng"
            onChange={handleFileUpload}
            disabled={uploading}
            style={{ display: "none" }}
          />
        </label>

        <button
          className="action-button sync"
          onClick={handleSync}
          disabled={syncing}
        >
          <RefreshCw size={16} className={syncing ? "spinning" : ""} />
          {syncing ? "Syncing..." : "Sync Database"}
        </button>

        <button className="action-button danger" onClick={handleClear}>
          <Trash2 size={16} />
          Clear Data
        </button>
      </div>

      {message && <div className="message success">{message}</div>}
      {error && <div className="message error">{error}</div>}
    </div>
  );
}

function App() {
  const { summary, flows, hosts, alerts, timeseries, protocols, error } = usePollingData();
  const distribution = useMemo(
    () => [
      { name: "Benign", value: summary.benign_flows || 0 },
      { name: "Botnet", value: summary.botnet_flows || 0 },
    ],
    [summary],
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Botnet Stream Monitor</h1>
          <p>Live flow predictions from replayed PCAP traffic</p>
        </div>
        <div className="connection-state">
          <span className={error ? "dot offline" : "dot"} />
          {error ? "API offline" : "Polling every 2s"}
        </div>
      </header>

      <UploadPanel />

      <section className="stats-grid">
        <StatCard icon={Activity} label="Total flows" value={summary.total_flows} tone="blue" />
        <StatCard icon={ShieldCheck} label="Benign flows" value={summary.benign_flows} tone="green" />
        <StatCard icon={AlertTriangle} label="Botnet flows" value={summary.botnet_flows} tone="red" />
        <StatCard icon={MonitorDot} label="Total hosts" value={summary.total_hosts} tone="teal" />
        <StatCard icon={Database} label="Botnet hosts" value={summary.botnet_hosts} tone="amber" />
        <StatCard icon={BarChart3} label="Active alerts" value={summary.active_alerts} tone="gray" />
      </section>

      <section className="chart-grid">
        <div className="panel">
          <h2>Flows Over Time</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={timeseries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" hide />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="benign" stroke="#26734d" strokeWidth={2} />
              <Line type="monotone" dataKey="botnet" stroke="#b42318" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <h2>Prediction Mix</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={distribution} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                <Cell fill="#26734d" />
                <Cell fill="#b42318" />
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <h2>Protocol Distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={protocols}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="protocol" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#1f6f8b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel wide">
          <h2>Live Flow Stream</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Source</th>
                  <th>Destination</th>
                  <th>Proto</th>
                  <th>Sport</th>
                  <th>Dport</th>
                  <th>Prediction</th>
                </tr>
              </thead>
              <tbody>
                {flows.map((flow) => (
                  <tr key={flow.id}>
                    <td>{flow.timestamp?.slice(11, 19)}</td>
                    <td>{flow.src_ip}</td>
                    <td>{flow.dst_ip}</td>
                    <td>{flow.protocol}</td>
                    <td>{flow.sport}</td>
                    <td>{flow.dport}</td>
                    <td>
                      <Badge value={flow.prediction} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <h2>Alerts</h2>
          <div className="alert-list">
            {alerts.length === 0 && <p className="empty">No alerts yet</p>}
            {alerts.map((alert) => (
              <article className="alert" key={alert.id}>
                <strong>{alert.src_ip}</strong>
                <span>{alert.botnet_percentage?.toFixed(1)}% botnet flows</span>
                <small>{alert.timestamp?.slice(11, 19)}</small>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Host Monitoring</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source IP</th>
                <th>Total</th>
                <th>Benign</th>
                <th>Botnet</th>
                <th>Botnet %</th>
                <th>Status</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {hosts.map((host) => (
                <tr key={host.src_ip}>
                  <td>{host.src_ip}</td>
                  <td>{host.total_flows}</td>
                  <td>{host.benign_flows}</td>
                  <td>{host.botnet_flows}</td>
                  <td>{host.botnet_percentage?.toFixed(1)}</td>
                  <td>
                    <Badge value={host.status} />
                  </td>
                  <td>{host.last_seen?.slice(11, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

