import pandas as pd
from sklearn.ensemble import IsolationForest

# In-memory storage (hackathon friendly)
transactions = []
project_risk = {}
notifications = []

# ⭐ Add transaction
def add_transaction(project_id, amount, approver):
    transactions.append({
        "project_id": project_id,
        "amount": amount,
        "approver": approver
    })


# ⭐ Detect anomaly
def detect_anomaly(project_id, amount):

    if len(transactions) < 5:
        return False, "Insufficient data"

    df = pd.DataFrame(transactions)

    # Isolation Forest
    model = IsolationForest(contamination=0.2, random_state=42)
    df["anomaly"] = model.fit_predict(df[["amount"]])

    latest = df.iloc[-1]["anomaly"]

    # ⭐ Explainability rule
    avg = df["amount"].mean()

    if amount > avg * 2:
        reason = "Amount unusually high compared to average"
        return True, reason

    if latest == -1:
        reason = "Statistical anomaly detected"
        return True, reason

    return False, "Normal transaction"


# ⭐ Risk score update
def update_risk(project_id, anomaly):
    if project_id not in project_risk:
        project_risk[project_id] = 0

    if anomaly:
        project_risk[project_id] += 20

    return project_risk[project_id]


# ⭐ Event notification
def create_notification(project_id, message):
    notifications.append({
        "project_id": project_id,
        "message": message
    })


# ⭐ Get notifications
def get_notifications():
    return notifications