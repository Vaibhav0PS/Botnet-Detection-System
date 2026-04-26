import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import pickle
import os

# Features to drop as per predictor.py
DROP_MODEL_COLUMNS = [
    "avg_sent_inter_times",
    "avg_rec_inter_times",
    "med_sent_inter_times",
    "med_rec_inter_times",
    "var_packet_size_rec",
    "var_packet_size_sent",
]

print("Loading dataset...")
df = pd.read_csv("training_dataset.csv")
print("Dataset shape:", df.shape)

# Preprocessing logic similar to detector/predictor.py
print("Preprocessing...")
# Filter flows (port > 1000 and pkts > 2)
df = df[df["sport"] > 1000]
df = df[df["total_pkts"] > 2]

# Drop unwanted columns
df = df.drop(columns=DROP_MODEL_COLUMNS)

# Encode protocol
le = LabelEncoder()
df["protocol"] = le.fit_transform(df["protocol"].astype(str))

# Save IPs but drop from training
y = df["label"].values
X = df.drop(columns=["label", "src_ip", "dst_ip"])

# Handle missing values
X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
X = X.astype("float64")

print(f"Features for training: {X.shape[1]}")

# Feature scaling
print("Scaling features...")
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# KMeans clustering (10 clusters as expected by predictor.py)
print("Training KMeans (10 clusters)...")
kmeans = KMeans(n_clusters=10, random_state=42)
cluster_labels = kmeans.fit_predict(X_scaled)

# Analysis of clusters to see which ones are mostly botnet
for i in range(10):
    mask = cluster_labels == i
    if np.any(mask):
        botnet_ratio = np.sum(y[mask]) / np.sum(mask)
        print(f"Cluster {i}: Botnet ratio = {botnet_ratio:.2f} ({np.sum(mask)} flows)")

# Random Forest
print("Training Random Forest...")
rf = RandomForestClassifier(
    n_estimators=300,
    max_features=None,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_scaled, y)

# Create Models directory if it doesn't exist
os.makedirs("Training_files/Models", exist_ok=True)

print("Saving models to Training_files/Models/...")
pickle.dump(kmeans, open("Training_files/Models/cluster.pkl", "wb"))
joblib.dump(rf, "Training_files/Models/flow_predictor.joblib")
pickle.dump(le, open("Training_files/Models/label_encoder.pkl", "wb"))
pickle.dump(scaler, open("Training_files/Models/mms.pkl", "wb"))

print("\nSuccess! Models have been retrained.")
print("To use them, copy the files from 'Training_files/Models/' to the root 'Models/' directory.")
