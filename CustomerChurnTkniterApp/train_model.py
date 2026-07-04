import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pickle

df = pd.read_csv("TelcoCustomerChurn.csv")

df["ChurnLabel"] = df["ChurnLabel"].map({"Yes":1,"No":0})

df["Contract_OneYear"] = (df["Contract"] == "One Year").astype(int)
df["Contract_TwoYear"] = (df["Contract"] == "Two Year").astype(int)

X = df[
    [
        "SatisfactionScore",
        "TenureinMonths",
        "MonthlyCharge",
        "Contract_OneYear",
        "Contract_TwoYear"
    ]
]

y = df["ChurnLabel"]

X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train,y_train)

accuracy = model.score(X_test,y_test)

pickle.dump(model, open("churn_model.pkl","wb"))
pickle.dump(accuracy, open("model_accuracy.pkl","wb"))

print("Model trained successfully")
print("Accuracy:", accuracy)