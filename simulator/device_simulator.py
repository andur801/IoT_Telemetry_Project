import requests
import random
import time

DEVICE_ID = 1  # Change this to match an existing device ID in your database
API_URL = f"http://127.0.0.1:8000/devices/{DEVICE_ID}/telemetry"
DEVICE_API_KEY = "a5eff3a6b62f6e8459e6fa2a1d197fdc"  # Change this to match the API key of the device

METRICS = [
    "temperature",
    "humidity",
    "battery"
]


def generate_value(metric):
    if metric == "temperature":
        return round(random.uniform(20, 25), 2)

    if metric == "humidity":
        return random.randint(40, 60)

    if metric == "battery":
        return round(random.uniform(3.5, 4.2), 2)


while True:
    metric = random.choice(METRICS)

    # payload = {
    #     "device_id": DEVICE_ID,
    #     "api_key": DEVICE_API_KEY,
    #     "metric_type": metric,
    #     "value": generate_value(metric)
    # }

    payload = {
        "metric_type": metric,
        "value": generate_value(metric)
    }

    headers = {
        "Authorization": f"Bearer {DEVICE_API_KEY}"
    }

    try:
        response = requests.post(
        API_URL,
        json=payload,
        headers=headers
    )

        print("Sent:", payload, "| Status:", response.status_code)

    except Exception as e:
        print("Error sending telemetry:", e)

    time.sleep(5)