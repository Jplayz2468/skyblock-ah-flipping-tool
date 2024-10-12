# UwU

import requests
import json
import pyperclip
from datetime import datetime
import time
from pynput import keyboard
import winsound
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
BASE_URL = "https://api.hypixel.net"
REFRESH_KEY = '`'

# Global variables
should_refresh = threading.Event()
suggested_auction_ids = set()
last_suggested_item_type = None

class AuctionFetcher:
    def __init__(self):
        self.session = requests.Session()

    def fetch_page(self, page):
        try:
            response = self.session.get(f"{BASE_URL}/skyblock/auctions?page={page}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching auctions page {page}: {e}")
            return None

    def fetch_all_auctions(self):
        first_page = self.fetch_page(0)
        if not first_page:
            return []

        total_pages = first_page.get("totalPages", 1)
        all_auctions = first_page.get("auctions", [])

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.fetch_page, page) for page in range(1, total_pages)]
            for future in as_completed(futures):
                page_data = future.result()
                if page_data:
                    all_auctions.extend(page_data.get("auctions", []))

        return all_auctions

class FlipFinder:
    def __init__(self, params):
        self.params = params
        self.fetcher = AuctionFetcher()

    @staticmethod
    def is_active_bin_auction(auction):
        return (not auction.get("claimed", False) and
                auction.get("end", 0) > int(time.time() * 1000) and
                auction.get("bin", False) and
                auction.get("highest_bid_amount", 0) == 0)

    @staticmethod
    def get_item_type(item_name):
        return ' '.join(item_name.split()[:2])

    def filter_auctions(self, auctions):
        return [
            auction for auction in auctions
            if (self.is_active_bin_auction(auction) and
                self.params["min_item_price"] <= auction.get("starting_bid", 0) <= self.params["max_buy_price"] and
                "attribute shard" not in auction.get("item_name", "").lower())
        ]

    def find_best_flip(self):
        global suggested_auction_ids, last_suggested_item_type

        all_auctions = self.fetcher.fetch_all_auctions()
        filtered_auctions = self.filter_auctions(all_auctions)

        item_groups = defaultdict(list)
        for auction in filtered_auctions:
            item_groups[auction["item_name"]].append(auction)

        for item_name, auctions in item_groups.items():
            if len(auctions) < self.params["min_sales_volume"]:
                continue

            sorted_auctions = sorted(auctions, key=lambda x: x["starting_bid"])
            lowest_auction = sorted_auctions[0]
            second_lowest_price = sorted_auctions[1]["starting_bid"] if len(sorted_auctions) > 1 else float('inf')

            potential_profit = second_lowest_price - lowest_auction["starting_bid"]
            profit_margin = (potential_profit / lowest_auction["starting_bid"]) * 100

            if (potential_profit >= self.params["min_profit"] and
                profit_margin <= self.params["max_profit_margin"] and
                lowest_auction["uuid"] not in suggested_auction_ids):

                item_type = self.get_item_type(item_name)
                if item_type != last_suggested_item_type:
                    suggested_auction_ids.add(lowest_auction["uuid"])
                    last_suggested_item_type = item_type
                    return {
                        "item": item_name,
                        "lowest_price": lowest_auction["starting_bid"],
                        "second_lowest_price": second_lowest_price,
                        "potential_profit": potential_profit,
                        "profit_margin": profit_margin,
                        "auction_id": lowest_auction["uuid"],
                        "sales_volume": len(auctions)
                    }

        return None

def on_press(key):
    if getattr(key, 'char', None) == REFRESH_KEY:
        should_refresh.set()
        logging.debug("Refresh key pressed")

def print_flip_info(flip):
    print(f"\nBest flip found:")
    print(f"Item: {flip['item']}")
    print(f"Lowest price: {flip['lowest_price']:,}")
    print(f"Second lowest price: {flip['second_lowest_price']:,}")
    print(f"Potential profit: {flip['potential_profit']:,}")
    print(f"Profit margin: {flip['profit_margin']:.2f}%")
    print(f"Sales volume: {flip['sales_volume']}")

    command = f"/viewauction {flip['auction_id']}"
    pyperclip.copy(command)
    print(f"\nLowest BIN auction command copied to clipboard: {command}")
    print("Paste this command in-game to view the auction.")
    print("\nCAUTION: Always double-check prices before purchasing!")
    print("Consider checking external price sources for additional verification.")

def main():
    print("Starting Hypixel BIN Flip Calculator...")
    print(f"Press '{REFRESH_KEY}' to refresh auctions.")

    params = {
        "threshold_percentage": float(input("Enter the minimum price difference threshold (default 20%): ") or 20),
        "min_profit": int(input("Enter the minimum profit in coins (default 10000): ") or 10000),
        "min_item_price": int(input("Enter the minimum item price in coins (default 100000): ") or 100000),
        "max_buy_price": int(input("Enter the maximum buy price in coins (default 1000000): ") or 1000000),
        "max_profit_margin": float(input("Enter the maximum profit margin percentage (default 50%): ") or 50),
        "min_sales_volume": int(input("Enter the minimum sales volume (default 5): ") or 5)
    }

    flip_finder = FlipFinder(params)

    keyboard.Listener(on_press=on_press).start()

    while True:
        if should_refresh.is_set():
            print(f"\nFetching auctions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
            best_flip = flip_finder.find_best_flip()
            if best_flip:
                print_flip_info(best_flip)
                winsound.Beep(1000, 500)
            else:
                print("No suitable flips found.")
            should_refresh.clear()

        time.sleep(0.5)

if __name__ == "__main__":
    main()
