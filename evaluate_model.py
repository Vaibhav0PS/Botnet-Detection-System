import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from joblib import load
import pickle as pk
from os import path as osp
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

# your existing predictions


# Load preprocessed file created by botnetdetect
data = pd.read_csv("flows_preprocessed_with_prediction.csv")

# Extract labels
y_true = data['label'].map({'Benign':0,'Botnet':1})

# Remove non-feature columns
X = data.drop(columns=['label','src_ip','dst_ip'], errors='ignore')

# Convert to numeric
X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

# Load scaler
mms = pk.load(open(osp.join("Models", "mms.pkl"),'rb'))
X = mms.transform(X)

# Load model
model = load(osp.join("Models", "flow_predictor.joblib"))

# Predict
y_pred = model.predict(X)

print("Confusion Matrix:")
print(confusion_matrix(y_true, y_pred))

print("\nClassification Report:")
print(classification_report(y_true, y_pred))

cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(6,5))
plt.imshow(cm, interpolation='nearest')
plt.title("Confusion Matrix")
plt.colorbar()

classes = ["Benign", "Botnet"]
tick_marks = np.arange(len(classes))
plt.xticks(tick_marks, classes)
plt.yticks(tick_marks, classes)

# write numbers inside boxes
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        plt.text(j, i, cm[i, j],
                 ha="center", va="center")

plt.ylabel("Actual")
plt.xlabel("Predicted")
plt.tight_layout()
plt.show()