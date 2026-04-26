import pickle as pk
from os import path as osp

import numpy as np
import pandas as pd
from joblib import load

from detector.feature_extractor import DROP_MODEL_COLUMNS, RAW_FEATURE_COLUMNS


BENIGN_CLASS_NAME = "Benign"
BOTNET_CLASS_NAME = "Botnet"
PRED_TO_RESULT = {0: BENIGN_CLASS_NAME, 1: BOTNET_CLASS_NAME}


class BotnetPredictor:
    def __init__(self, models_dir="Models"):
        self.models_dir = models_dir
        print(f"[PREDICTOR] Loading models from {models_dir}...")
        try:
            self.label_encoder = pk.load(open(osp.join(models_dir, "label_encoder.pkl"), "rb"))
            self.scaler = pk.load(open(osp.join(models_dir, "mms.pkl"), "rb"))
            if not hasattr(self.scaler, "clip"):
                self.scaler.clip = False
            self.cluster = pk.load(open(osp.join(models_dir, "cluster.pkl"), "rb"))
            if not hasattr(self.cluster, "_n_threads"):
                self.cluster._n_threads = 1
            print(f"[PREDICTOR] Core models loaded successfully. KMeans clusters: {self.cluster.n_clusters}")
        except Exception as e:
            print(f"[PREDICTOR] ERROR: Failed to load core models: {e}")
            raise

        try:
            self.classifier = load(osp.join(models_dir, "flow_predictor.joblib"))
            self.classifier_load_error = None
            print("[PREDICTOR] Classifier loaded successfully.")
        except Exception as ex:
            self.classifier = None
            self.classifier_load_error = ex
            print(f"[PREDICTOR] WARNING: flow_predictor.joblib load failed: {ex}")
            print("[PREDICTOR] Using cluster-only fallback. ALL non-explicitly-clustered flows will be BENIGN.")

    def preprocess_records(self, records):
        if not records:
            return np.array([]), pd.Series([]), pd.Series([]), pd.DataFrame()
        frame = pd.DataFrame(records, columns=RAW_FEATURE_COLUMNS)
        return self.preprocess_dataframe(frame)

    def preprocess_dataframe(self, frame):
        frame = frame.copy()
        
        # Keep track of original size
        original_count = len(frame)
        
        frame = frame[frame["sport"] > 1000]
        frame = frame[frame["total_pkts"] > 2]
        
        filtered_count = len(frame)
        if filtered_count < original_count:
            # print(f"[PREDICTOR] Filtered out {original_count - filtered_count} flows (port <= 1000 or pkts <= 2)")
            pass

        if frame.empty:
            return np.array([]), pd.Series([]), pd.Series([]), frame

        frame.drop(DROP_MODEL_COLUMNS, axis=1, inplace=True)
        
        try:
            frame["protocol"] = self.label_encoder.transform(frame["protocol"].astype(str))
        except Exception as e:
            # Fallback if label encoder fails (e.g. unknown protocol)
            frame["protocol"] = 0
            
        src_ip = frame["src_ip"].copy()
        dst_ip = frame["dst_ip"].copy()
        frame.drop(["src_ip", "dst_ip"], axis=1, inplace=True)
        
        frame["var_packet_size"] = pd.to_numeric(frame["var_packet_size"], errors="coerce")
        # Keep index consistency
        valid_mask = frame["var_packet_size"].notna()
        frame = frame[valid_mask]
        src_ip = src_ip[valid_mask]
        dst_ip = dst_ip[valid_mask]
        
        frame = frame.astype("float64")
        return frame.values, src_ip, dst_ip, frame

    def predict_features(self, features):
        if len(features) == 0:
            return []
            
        features = np.array(features, dtype=float)
        features = self.scaler.transform(features)
        
        # Predict clusters and class
        cluster_labels = self.cluster.predict(features)

        if self.classifier is None:
            # Fallback to zeros if classifier is missing
            model_labels = np.zeros(len(cluster_labels), dtype=int)
            # If we only have clusters, we could try to use them, 
            # but without hardcoded mapping it's safer to stay benign
            # unless we find a specific cluster that is always botnet.
        else:
            model_labels = self.classifier.predict(features)

        # We now trust the Random Forest classifier for all flows.
        # The KMeans clustering can still be used for visualization or 
        # further refinement, but we remove the hardcoded overrides
        # that break when the model is retrained.
        labels = [int(label) for label in model_labels]
        
        return labels

    def predict_records(self, records):
        features, src_ip, dst_ip, frame = self.preprocess_records(records)
        labels = self.predict_features(features) if len(features) else []
        return labels, src_ip, dst_ip, frame


def label_results(labels):
    return [PRED_TO_RESULT[int(label)] for label in labels]

