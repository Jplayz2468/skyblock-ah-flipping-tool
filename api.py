import requests
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, jsonify, render_template_string
from threading import Thread

# Constants
BASE_URL = "https://api.hypixel.net/skyblock/auctions"
DATA_FILE = "auction_data.json"

# Initialize data storage
data = defaultdict(lambda: {"prices": [], "last_updated": None})

app = Flask(__name__)

def fetch_auctions():
    all_auctions = []
    page = 0
    while True:
        response = requests.get(f"{BASE_URL}?page={page}")
        auction_data = response.json()
        all_auctions.extend(auction_data["auctions"])
        if page >= auction_data["totalPages"] - 1:
            break
        page += 1
    return all_auctions

def process_auctions():
    print("Fetching and processing auctions...")
    auctions = fetch_auctions()
    current_data = {}

    for auction in auctions:
        if not auction.get("bin", False):
            continue

        item_id = auction["item_name"]
        price = auction["starting_bid"]

        # Ignore stars, reforges, and other modifications
        item_id = item_id.split("[")[0].strip()
        item_id = item_id.split("✪")[0].strip()

        if item_id not in current_data or price < current_data[item_id]:
            current_data[item_id] = price

    current_time = datetime.now()
    for item_id, price in current_data.items():
        data[item_id]["prices"].append((current_time, price))
        data[item_id]["last_updated"] = current_time

    # Remove data older than 3 days
    three_days_ago = current_time - timedelta(days=3)
    for item_id in data:
        data[item_id]["prices"] = [(t, p) for t, p in data[item_id]["prices"] if t > three_days_ago]

    print(f"Processed {len(current_data)} items.")

def save_data():
    print("Saving data...")
    with open(DATA_FILE, "w") as f:
        json.dump({k: v for k, v in data.items()}, f, default=str)

def load_data():
    global data
    try:
        with open(DATA_FILE, "r") as f:
            loaded_data = json.load(f)
            for item_id, item_data in loaded_data.items():
                data[item_id]["prices"] = [(datetime.fromisoformat(t), p) for t, p in item_data["prices"]]
                data[item_id]["last_updated"] = datetime.fromisoformat(item_data["last_updated"])
        print("Data loaded successfully.")
    except FileNotFoundError:
        print("No existing data file found. Starting fresh.")

def background_task():
    while True:
        process_auctions()
        save_data()
        print("Sleeping for 5 minutes...")
        time.sleep(300)  # Sleep for 5 minutes

@app.route('/')
def home():
    return render_template_string("""
    <h1>Hypixel 3-Day Average Lowest BIN Tracker</h1>
    <p>Use the /item/[item_name] endpoint to get the 3-day average lowest BIN for a specific item.</p>
    <p>Example: <a href="/item/Hyperion">/item/Hyperion</a></p>
    """)

@app.route('/item/<key>/<item_name>')
def item_price(key, item_name):
    if key == 'MazH2JtZeLCxIydNaWSaqHEpZvy3p1TS':
        pass
    else:
        return jsonify({"error": "Invalid key"})
    item_data = data.get(item_name, {"prices": [], "last_updated": None})

    if not item_data["prices"]:
        return jsonify({"error": "Item not found or no data available"}), 404

    three_day_avg = sum(price for _, price in item_data["prices"]) / len(item_data["prices"])

    return jsonify({
        "item_name": item_name,
        "three_day_avg_lowest_bin": three_day_avg,
        "last_updated": item_data["last_updated"],
        "data_points": len(item_data["prices"])
    })

if __name__ == "__main__":
    load_data()

    # Start the background task in a separate thread
    thread = Thread(target=background_task)
    thread.start()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)