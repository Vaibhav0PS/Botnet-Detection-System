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
        self.label_encoder = pk.load(open(osp.join(models_dir, "label_encoder.pkl"), "rb"))
        self.scaler = pk.load(open(osp.join(models_dir, "mms.pkl"), "rb"))
        if not hasattr(self.scaler, "clip"):
            self.scaler.clip = False
        self.cluster = pk.load(open(osp.join(models_dir, "cluster.pkl"), "rb"))
        if not hasattr(self.cluster, "_n_threads"):
            self.cluster._n_threads = 1
        try:
            self.classifier = load(osp.join(models_dir, "flow_predictor.joblib"))
            self.classifier_load_error = None
        except Exception as ex:
            self.classifier = None
            self.classifier_load_error = ex

    def preprocess_records(self, records):
        frame = pd.DataFrame(records, columns=RAW_FEATURE_COLUMNS)
        return self.preprocess_dataframe(frame)

    def preprocess_dataframe(self, frame):
        frame = frame.copy()
        frame = frame[frame["sport"] > 1000]
        frame = frame[frame["total_pkts"] > 2]
        frame.drop(DROP_MODEL_COLUMNS, axis=1, inplace=True)
        frame["protocol"] = self.label_encoder.transform(frame["protocol"])

        src_ip = frame["src_ip"].copy()
        dst_ip = frame["dst_ip"].copy()
        frame.drop(["src_ip", "dst_ip"], axis=1, inplace=True)
        frame["var_packet_size"] = pd.to_numeric(frame["var_packet_size"], errors="coerce")
        frame = frame[frame["var_packet_size"].notna()]
        src_ip = src_ip.loc[frame.index]
        dst_ip = dst_ip.loc[frame.index]
        frame = frame.astype("float64")
        return frame.values, src_ip, dst_ip, frame

    def predict_features(self, features):
        features = np.array(features, dtype=float)
        features = self.scaler.transform(features)
        cluster_labels = self.cluster.predict(features)

        if self.classifier is None:
            print(
                "Warning: flow_predictor.joblib is incompatible with current sklearn. "
                "Using cluster-only prediction fallback. Details:",
                self.classifier_load_error,
            )
            model_labels = np.zeros(len(cluster_labels), dtype=int)
        else:
            model_labels = self.classifier.predict(features)

        labels = []
        for i, cluster_label in enumerate(cluster_labels):
            if cluster_label in (1, 2, 5, 8):
                labels.append(0)
            elif cluster_label == 6:
                labels.append(1)
            else:
                labels.append(int(model_labels[i]))
        return labels

    def predict_records(self, records):
        features, src_ip, dst_ip, frame = self.preprocess_records(records)
        labels = self.predict_features(features) if len(features) else []
        return labels, src_ip, dst_ip, frame


def label_results(labels):
    return [PRED_TO_RESULT[int(label)] for label in labels]

