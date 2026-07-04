# test_project.py

import pandas as pd
from project import calculate_churn_rate, get_high_risk_customers

def test_calculate_churn_rate():
    df = pd.DataFrame({
        "ChurnLabel": ["Yes", "No", "Yes"]
    })
    assert calculate_churn_rate(df) == 66.67

def test_get_high_risk_customers():
    df = pd.DataFrame({
        "SatisfactionScore": [3, 7, 2]
    })
    result = get_high_risk_customers(df)
    assert len(result) == 2

def test_empty_data():
    df = pd.DataFrame({"ChurnLabel": []})
    assert calculate_churn_rate(df) == 0