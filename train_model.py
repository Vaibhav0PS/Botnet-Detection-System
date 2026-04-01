import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score
import joblib

# load dataset
data = pd.read_csv("training_dataset.csv")

# split features and label
X = data.drop("label", axis=1)
y = data["label"]

# normalize features
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# train model
model = RandomForestClassifier(n_estimators=200)
model.fit(X_train, y_train)

# evaluate
pred = model.predict(X_test)
accuracy = accuracy_score(y_test, pred)

print("Model Accuracy:", accuracy)

# save model
joblib.dump(model, "Models/retrained_model.pkl")
joblib.dump(scaler, "Models/scaler.pkl")