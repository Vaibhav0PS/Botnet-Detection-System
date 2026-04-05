import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

# Load dataset
data = pd.read_csv("flows_preprocessed_with_prediction.csv")

# Remove non-numeric columns
X = data.drop(columns=['label','src_ip','dst_ip'], errors='ignore')
X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

# Scale data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# PCA (use scaled data)
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

# KMeans
kmeans = KMeans(n_clusters=5, random_state=42)
clusters = kmeans.fit_predict(X_pca)

# Plot
plt.figure(figsize=(8,6))
plt.scatter(X_pca[:,0], X_pca[:,1], c=clusters)

# Centroids
centroids = kmeans.cluster_centers_
plt.scatter(centroids[:,0], centroids[:,1], s=200, marker='o')

plt.title("KMeans Clustering")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.show()