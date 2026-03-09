from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from pydantic import BaseModel
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque

# Model yükle
with open("british_airways_model.pkl", "rb") as f:
    saved_data = pickle.load(f)
    model = saved_data["model"]
    scaler = saved_data["scaler"]
    encoders = saved_data["encoders"]

# CSV veri setini yükle (analitik için)
df_raw = pd.read_csv("data/customer_booking.csv", encoding="ISO-8859-1")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# In-memory tahmin geçmişi
prediction_history = deque(maxlen=50)
prediction_stats = {
    "total": 0,
    "completed": 0,
    "not_completed": 0,
    "prob_sum": 0.0,
    "routes": {},
}


class CustomerData(BaseModel):
    num_passengers: int
    sales_channel: str
    trip_type: str
    purchase_lead: int
    length_of_stay: int
    flight_hour: int
    flight_day: str  # "Mon", "Tue" vs.
    flight_duration: float
    booking_origin: str
    route: str  # "LHRIST" gibi, origin+destination buradan üretilecek
    wants_extra_baggage: int
    wants_preferred_seat: int
    wants_in_flight_meals: int


def preprocess(data: dict) -> pd.DataFrame:
    df = pd.DataFrame([data])

    # 1. flight_day mapping
    mapping = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}
    df["flight_day"] = df["flight_day"].map(mapping)

    # 2. route → origin + destination
    df["origin"] = df["route"].str[:3]
    df["destination"] = df["route"].str[3:]
    df = df.drop(columns=["route"])

    # 3. booking_origin gruplama
    popular_countries = [
        "United Kingdom",
        "Australia",
        "Malaysia",
        "Hong Kong",
        "South Korea",
        "Japan",
        "Singapore",
        "India",
        "Thailand",
        "China",
        "Taiwan",
        "Indonesia",
        "New Zealand",
    ]
    if df["booking_origin"].iloc[0] not in popular_countries:
        df["booking_origin"] = "Other"

    # 4. Label Encoding
    for col in ["sales_channel", "trip_type"]:
        df[col] = encoders[col].transform(df[col])

    # 5. Target Encoding
    high_card_cols = ["booking_origin", "origin", "destination"]
    df[high_card_cols] = encoders["target_encoder"].transform(df[high_card_cols])

    # 6. Scaling
    num_cols = [
        "num_passengers",
        "purchase_lead",
        "length_of_stay",
        "flight_hour",
        "flight_day",
        "flight_duration",
    ]
    df[num_cols] = scaler.transform(df[num_cols])

    feature_cols = [
        "num_passengers",
        "sales_channel",
        "trip_type",
        "purchase_lead",
        "length_of_stay",
        "flight_hour",
        "flight_day",
        "booking_origin",
        "wants_extra_baggage",
        "wants_preferred_seat",
        "wants_in_flight_meals",
        "flight_duration",
        "origin",
        "destination",
    ]
    df = df[feature_cols]

    return df


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/predict")
def predict(data: CustomerData):
    df = preprocess(data.dict())

    prediction = int(model.predict(df)[0])
    probability = round(float(model.predict_proba(df)[0][1]), 4)

    # Tahmin geçmişine kaydet
    entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "route": data.route,
        "origin": data.booking_origin,
        "passengers": data.num_passengers,
        "channel": data.sales_channel,
        "trip_type": data.trip_type,
        "prediction": prediction,
        "probability": probability,
    }
    prediction_history.appendleft(entry)

    # İstatistikleri güncelle
    prediction_stats["total"] += 1
    if prediction == 1:
        prediction_stats["completed"] += 1
    else:
        prediction_stats["not_completed"] += 1
    prediction_stats["prob_sum"] += probability
    prediction_stats["routes"][data.route] = (
        prediction_stats["routes"].get(data.route, 0) + 1
    )

    return {
        "booking_complete": prediction,
        "probability": probability,
        "message": "Rezervasyon tamamlanır ✅"
        if prediction == 1
        else "Rezervasyon tamamlanmaz ❌",
    }


# ── ANALYTICS ENDPOINTS ──


@app.get("/api/analytics")
def get_analytics():
    df = df_raw.copy()
    total = len(df)
    completed = int(df["booking_complete"].sum())
    not_completed = total - completed
    completion_rate = round(completed / total * 100, 1)

    # Satış kanalı dağılımı
    channel_dist = df["sales_channel"].value_counts().to_dict()

    # Seyahat tipi dağılımı
    trip_dist = df["trip_type"].value_counts().to_dict()

    # Günlere göre dağılım
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_counts = df["flight_day"].value_counts().reindex(day_order, fill_value=0).to_dict()

    # Günlere göre tamamlanma oranı
    day_completion = {}
    for day in day_order:
        day_df = df[df["flight_day"] == day]
        if len(day_df) > 0:
            day_completion[day] = round(
                day_df["booking_complete"].mean() * 100, 1
            )
        else:
            day_completion[day] = 0

    # Saatlere göre tamamlanma oranı
    hour_completion = {}
    for h in range(24):
        h_df = df[df["flight_hour"] == h]
        if len(h_df) > 0:
            hour_completion[str(h)] = round(h_df["booking_complete"].mean() * 100, 1)
        else:
            hour_completion[str(h)] = 0

    # Top 10 rota
    top_routes = (
        df["route"].value_counts().head(10).to_dict()
    )

    # Top 10 ülke
    top_countries = (
        df["booking_origin"].value_counts().head(10).to_dict()
    )

    # Ortalamalar
    avg_stay = round(df["length_of_stay"].mean(), 1)
    avg_lead = round(df["purchase_lead"].mean(), 1)
    avg_duration = round(df["flight_duration"].mean(), 1)
    avg_passengers = round(df["num_passengers"].mean(), 1)

    return {
        "total": total,
        "completed": completed,
        "not_completed": not_completed,
        "completion_rate": completion_rate,
        "channel_distribution": channel_dist,
        "trip_distribution": trip_dist,
        "day_counts": day_counts,
        "day_completion": day_completion,
        "hour_completion": hour_completion,
        "top_routes": top_routes,
        "top_countries": top_countries,
        "avg_stay": avg_stay,
        "avg_lead": avg_lead,
        "avg_duration": avg_duration,
        "avg_passengers": avg_passengers,
    }


@app.get("/api/feature-importance")
def get_feature_importance():
    feature_names = [
        "num_passengers",
        "sales_channel",
        "trip_type",
        "purchase_lead",
        "length_of_stay",
        "flight_hour",
        "flight_day",
        "booking_origin",
        "wants_extra_baggage",
        "wants_preferred_seat",
        "wants_in_flight_meals",
        "flight_duration",
        "origin",
        "destination",
    ]

    feature_labels = {
        "num_passengers": "Yolcu Sayısı",
        "sales_channel": "Satış Kanalı",
        "trip_type": "Seyahat Tipi",
        "purchase_lead": "Erken Satın Alma (gün)",
        "length_of_stay": "Konaklama Süresi",
        "flight_hour": "Uçuş Saati",
        "flight_day": "Uçuş Günü",
        "booking_origin": "Rezervasyon Kökeni",
        "wants_extra_baggage": "Ekstra Bagaj",
        "wants_preferred_seat": "Tercihli Koltuk",
        "wants_in_flight_meals": "Uçak İçi Yemek",
        "flight_duration": "Uçuş Süresi",
        "origin": "Kalkış Noktası",
        "destination": "Varış Noktası",
    }

    importances = model.feature_importances_.tolist()

    features = []
    for name, imp in zip(feature_names, importances):
        features.append(
            {
                "name": name,
                "label": feature_labels.get(name, name),
                "importance": round(imp, 4),
            }
        )

    # Önem sırasına göre sırala
    features.sort(key=lambda x: x["importance"], reverse=True)

    return {"features": features}


@app.get("/api/cohort")
def get_cohort():
    df = df_raw.copy()

    # Satış kanalı × Seyahat tipi kırılımında tamamlanma oranı
    cohort = (
        df.groupby(["sales_channel", "trip_type"])["booking_complete"]
        .agg(["mean", "count"])
        .reset_index()
    )
    cohort["mean"] = (cohort["mean"] * 100).round(1)
    cohort.columns = ["channel", "trip_type", "completion_rate", "count"]

    # Matris formatına dönüştür
    channels = sorted(df["sales_channel"].unique().tolist())
    trip_types = sorted(df["trip_type"].unique().tolist())

    matrix = {}
    counts_matrix = {}
    for _, row in cohort.iterrows():
        key = row["channel"]
        if key not in matrix:
            matrix[key] = {}
            counts_matrix[key] = {}
        matrix[key][row["trip_type"]] = row["completion_rate"]
        counts_matrix[key][row["trip_type"]] = int(row["count"])

    # Ekstra bagaj × tamamlanma
    baggage_cohort = (
        df.groupby("wants_extra_baggage")["booking_complete"]
        .mean()
        .round(3)
        .to_dict()
    )

    # Tercihli koltuk × tamamlanma
    seat_cohort = (
        df.groupby("wants_preferred_seat")["booking_complete"]
        .mean()
        .round(3)
        .to_dict()
    )

    # Yemek × tamamlanma
    meal_cohort = (
        df.groupby("wants_in_flight_meals")["booking_complete"]
        .mean()
        .round(3)
        .to_dict()
    )

    return {
        "channels": channels,
        "trip_types": trip_types,
        "matrix": matrix,
        "counts": counts_matrix,
        "extras": {
            "baggage": {str(k): round(v * 100, 1) for k, v in baggage_cohort.items()},
            "seat": {str(k): round(v * 100, 1) for k, v in seat_cohort.items()},
            "meal": {str(k): round(v * 100, 1) for k, v in meal_cohort.items()},
        },
    }


@app.get("/api/predictions/recent")
def get_recent_predictions():
    return {"predictions": list(prediction_history)}


@app.get("/api/metrics")
def get_metrics():
    total = prediction_stats["total"]
    if total == 0:
        return {
            "total_predictions": 0,
            "completion_rate": 0,
            "avg_probability": 0,
            "top_route": "-",
            "completed": 0,
            "not_completed": 0,
        }

    avg_prob = round(prediction_stats["prob_sum"] / total * 100, 1)
    comp_rate = round(prediction_stats["completed"] / total * 100, 1)

    top_route = "-"
    if prediction_stats["routes"]:
        top_route = max(
            prediction_stats["routes"], key=prediction_stats["routes"].get
        )

    return {
        "total_predictions": total,
        "completion_rate": comp_rate,
        "avg_probability": avg_prob,
        "top_route": top_route,
        "completed": prediction_stats["completed"],
        "not_completed": prediction_stats["not_completed"],
    }
