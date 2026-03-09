import pickle
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score

# Model yükle
with open("british_airways_model.pkl", "rb") as f:
    saved_data = pickle.load(f)

model = saved_data["model"]
scaler = saved_data["scaler"]
encoders = saved_data["encoders"]

# 1. Veriyi yükle
df = pd.read_csv("data/customer_booking.csv", encoding="ISO-8859-1")

# 2. flight_day mapping
mapping = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}
df["flight_day"] = df["flight_day"].map(mapping)

# 3. route → origin + destination
df["origin"] = df["route"].str[:3]
df["destination"] = df["route"].str[3:]
df = df.drop(columns=["route"])

# 4. Outlier baskılama
num_cols = [
    "num_passengers",
    "purchase_lead",
    "length_of_stay",
    "flight_hour",
    "flight_day",
    "flight_duration",
]


def outlier_thresholds(dataframe, col_name, q1=0.05, q3=0.95):
    quartile1 = dataframe[col_name].quantile(q1)
    quartile3 = dataframe[col_name].quantile(q3)
    iqr = quartile3 - quartile1
    return quartile1 - 1.5 * iqr, quartile3 + 1.5 * iqr


for col in num_cols:
    low, up = outlier_thresholds(df, col)
    df[col] = df[col].astype(float).clip(lower=low, upper=up)

# 5. booking_origin gruplama (nadir → 'Other')
popular_countries = (
    df["booking_origin"]
    .value_counts()[df["booking_origin"].value_counts() > 1000]
    .index
)
df.loc[~df["booking_origin"].isin(popular_countries), "booking_origin"] = "Other"

# 6. Label Encoding
for col in ["sales_channel", "trip_type"]:
    df[col] = encoders[col].transform(df[col])

# 7. Target Encoding
high_card_cols = ["booking_origin", "origin", "destination"]
df[high_card_cols] = encoders["target_encoder"].transform(df[high_card_cols])

# 8. Scaling
df[num_cols] = scaler.transform(df[num_cols])

# 9. Tahmin
y = df["booking_complete"]
X = df.drop("booking_complete", axis=1)

y_pred = model.predict(X)
y_proba = model.predict_proba(X)[:, 1]

print(classification_report(y, y_pred))
print(f"AUC-ROC: {roc_auc_score(y, y_proba):.4f}")
