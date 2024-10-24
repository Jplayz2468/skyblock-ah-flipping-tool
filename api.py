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
    try:
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
        
        # Update data with new prices
        for item_id, price in current_data.items():
            # Remove old prices before adding new one
            if item_id in data:
                data[item_id]["prices"] = [
                    (t, p) for t, p in data[item_id]["prices"]
                    if (current_time - t).total_seconds() < 259200  # 3 days in seconds
                ]
            data[item_id]["prices"].append((current_time, price))
            data[item_id]["last_updated"] = current_time

        # Clean up items with no recent data
        items_to_remove = []
        for item_id in data:
            if not data[item_id]["prices"]:
                items_to_remove.append(item_id)
        
        for item_id in items_to_remove:
            del data[item_id]

        print(f"Processed {len(current_data)} items.")
    except Exception as e:
        print(f"Error processing auctions: {str(e)}")

def save_data():
    print("Saving data...")
    try:
        with open(DATA_FILE, "w") as f:
            serialized_data = {}
            for item_id, item_data in data.items():
                serialized_data[item_id] = {
                    "prices": [(t.isoformat(), p) for t, p in item_data["prices"]],
                    "last_updated": item_data["last_updated"].isoformat() if item_data["last_updated"] else None
                }
            json.dump(serialized_data, f)
    except Exception as e:
        print(f"Error saving data: {str(e)}")

def load_data():
    global data
    try:
        with open(DATA_FILE, "r") as f:
            loaded_data = json.load(f)
            current_time = datetime.now()
            
            for item_id, item_data in loaded_data.items():
                # Only load data that's less than 3 days old
                prices = [
                    (datetime.fromisoformat(t), p) 
                    for t, p in item_data["prices"]
                    if (current_time - datetime.fromisoformat(t)).total_seconds() < 259200
                ]
                
                if prices:  # Only add items that have recent data
                    data[item_id]["prices"] = prices
                    data[item_id]["last_updated"] = datetime.fromisoformat(item_data["last_updated"]) if item_data["last_updated"] else None
                    
        print("Data loaded successfully.")
    except FileNotFoundError:
        print("No existing data file found. Starting fresh.")
    except Exception as e:
        print(f"Error loading data: {str(e)}")

def background_task():
    while True:
        try:
            process_auctions()
            save_data()
            print("Sleeping for 5 minutes...")
            time.sleep(300)  # Sleep for 5 minutes
        except Exception as e:
            print(f"Error in background task: {str(e)}")
            time.sleep(60)  # Sleep for 1 minute before retrying

@app.route('/')
def home():
    return render_template_string("""
    <h1>Hypixel 3-Day Average Lowest BIN Tracker</h1>
    <p>Use the /item/[key]/[item_name] endpoint to get the 3-day average lowest BIN for a specific item.</p>
    <p>Example: <a href="/item/MazH2JtZeLCxIydNaWSaqHEpZvy3p1TS/Hyperion">/item/[key]/Hyperion</a></p>
    """)

@app.route('/item/<key>/<item_name>')
def item_price(key, item_name):
    if key != 'MazH2JtZeLCxIydNaWSaqHEpZvy3p1TS':
        return jsonify({"error": "Invalid key"}), 401

    item_data = data.get(item_name)
    
    if not item_data or not item_data["prices"]:
        return jsonify({"error": "Item not found or no data available"}), 404

    current_time = datetime.now()
    recent_prices = [
        (t, p) for t, p in item_data["prices"]
        if (current_time - t).total_seconds() < 259200
    ]

    if not recent_prices:
        return jsonify({"error": "No recent data available"}), 404

    three_day_avg = sum(price for _, price in recent_prices) / len(recent_prices)
    
    return jsonify({
        "item_name": item_name,
        "three_day_avg_lowest_bin": three_day_avg,
        "last_updated": item_data["last_updated"].isoformat(),
        "data_points": len(recent_prices),
        "oldest_data_point": min(t.isoformat() for t, _ in recent_prices),
        "newest_data_point": max(t.isoformat() for t, _ in recent_prices)
    })

if __name__ == "__main__":
    load_data()

    # Start the background task in a separate thread
    thread = Thread(target=background_task, daemon=True)
    thread.start()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)