import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# -----------------------------
# Load dataset
# -----------------------------
data = pd.read_csv("TelcoCustomerChurn.csv")

data["ChurnLabel"] = data["ChurnLabel"].map({"No": 0, "Yes": 1})

data = data.drop([
    "CustomerID", "ChurnCategory", "ChurnReason",
    "CustomerStatus", "ChurnScore", "CLTV",
    "Country", "State", "City", "ZipCode",
    "Latitude", "Longitude"
], axis=1)

# -----------------------------
# Separate features & target
# -----------------------------
X = data.drop("ChurnLabel", axis=1)
y = data["ChurnLabel"]

# -----------------------------
# Encode categorical variables
# -----------------------------
X = pd.get_dummies(X, drop_first=True)

# -----------------------------
# Train-Test Split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()

X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# -----------------------------
# Logistic Regression (Baseline)
# -----------------------------
log_model = LogisticRegression(max_iter=10000)
log_model.fit(X_train, y_train)

log_pred = log_model.predict(X_test)
print("Logistic Accuracy:", accuracy_score(y_test, log_pred))

# -----------------------------
# Random Forest (Final Model)
# -----------------------------
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

rf_pred = model.predict(X_test)

print("Random Forest Accuracy:", accuracy_score(y_test, rf_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, rf_pred))
print("\nClassification Report:\n", classification_report(y_test, rf_pred))

# -----------------------------
# Save Files
# -----------------------------
pickle.dump(list(X.columns), open("model_columns.pkl", "wb"))
pickle.dump(model, open("churn_model.pkl", "wb"))


model_accuracy = accuracy_score(y_test, rf_pred)
pickle.dump(model_accuracy, open("model_accuracy.pkl", "wb"))

print("All files saved successfully!")









