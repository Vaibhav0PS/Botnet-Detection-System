import pandas as pd
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
import joblib

print("Loading dataset...")

df = pd.read_csv("training_dataset.csv", low_memory=False)

print("Dataset shape:", df.shape)

# Remove non-numeric columns like IP addresses
non_numeric_cols = df.select_dtypes(include=['object']).columns
print("Dropping non numeric columns:", non_numeric_cols)

df = df.drop(columns=non_numeric_cols)

print("Dataset after cleaning:", df.shape)

# Assume last column is label
X = df.iloc[:, :-1]
y = df.iloc[:, -1]

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Feature scaling
print("Scaling features...")
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# KMeans clustering
print("Training KMeans...")
kmeans = KMeans(n_clusters=2, random_state=42)
kmeans.fit(X_scaled)

# Random Forest
print("Training Random Forest...")
rf = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)

rf.fit(X_scaled, y_encoded)

print("Saving models...")

joblib.dump(kmeans, "Training_files/Models/cluster.pkl")
joblib.dump(rf, "Training_files/Models/flow_predictor.joblib")
joblib.dump(le, "Training_files/Models/label_encoder.pkl")
joblib.dump(scaler, "Training_files/Models/mms.pkl")

print("Training completed successfully!")