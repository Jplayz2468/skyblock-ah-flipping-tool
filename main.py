import requests
import json
import pyperclip
from datetime import datetime
import time
import winsound
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
HYPIXEL_API_BASE_URL = "https://api.hypixel.net"
PRICE_API_BASE_URL = "http://195.201.18.228:5000/item"
API_KEY = "MazH2JtZeLCxIydNaWSaqHEpZvy3p1TS"  # Replace with your actual API key
REFRESH_INTERVAL = 60  # seconds

class AuctionFetcher:
    def __init__(self):
        self.session = requests.Session()

    def fetch_page(self, page):
        try:
            response = self.session.get(f"{HYPIXEL_API_BASE_URL}/skyblock/auctions?page={page}")
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

class PriceFetcher:
    def __init__(self):
        self.session = requests.Session()

    def fetch_price_data(self, item_name):
        try:
            url = f"{PRICE_API_BASE_URL}/{API_KEY}/{item_name}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching price data for {item_name}: {e}")
            return None

class FlipFinder:
    def __init__(self, params):
        self.params = params
        self.auction_fetcher = AuctionFetcher()
        self.price_fetcher = PriceFetcher()

    @staticmethod
    def is_active_bin_auction(auction):
        return (not auction.get("claimed", False) and
                auction.get("end", 0) > int(time.time() * 1000) and
                auction.get("bin", False) and
                auction.get("highest_bid_amount", 0) == 0)

    @staticmethod
    def get_clean_item_name(item_name):
        # Remove stars, brackets, and common prefixes
        prefixes = ["Deadly", "Robust", "Blended", "Lumberjack's", "Dimensional", "Greater Spook", "Lustrous", "Glacial", "Fanged", "Jerry's", "Gentle", "Odd", "Fast", "Fair", "Epic", "Sharp", "Heroic", "Spicy", "Legendary", "Dirty", "Fabled", "Suspicious", "Gilded", "Warped", "Withered", "Bulky", "Stellar", "Heated", "Ambered", "Fruitful", "Magnetic", "Fleet", "Mithraic", "Auspicious", "Refined", "Blessed", "Toil", "Bountiful", "Loving", "Ridiculous", "Necrotic", "Giant", "Empowered", "Ancient", "Sweet", "Moil", "Silky", "Bloody", "Shaded", "Precise", "Spiritual", "Headstrong", "Clean", "Fierce", "Heavy", "Light", "Perfect", "Neat", "Elegant", "Fine", "Grand", "Hasty", "Rapid", "Unreal", "Awkward", "Rich", "Spiked", "Renowned", "Cubic", "Reinforced", "Salty", "Treacherous", "Stiff", "Lucky", "Very", "Highly", "Extremely", "Absolutely", "Even More", "Smart", "Titanic", "Wise", "Strong", "Unstable", "Superior", "Pure", "Holy", "Candied", "Submerged", "Bizarre", "Mythic", "Strengthened", "Jaded", "Zealous", "Godly", "Demonic", "Forceful", "Hurtful", "Strong", "Unpleasant", "Keen", "Pretty", "Shiny", "Simple", "Strange", "Vivid", "Bizarre", "Itchy", "Ominous", "Pleasant", "Pretty", "Shiny", "Simple", "Strange", "Vivid", "Awful", "Lush", "Pitiful", "Raider's", "Refurbished", "Festive", "Green Thumb", "Rooted", "Blooming", "Earthy", "Mossy", "Milky", "Signature", "Unyielding", "Dirty", "Stranded", "Chomp", "Pitchin'", "Glistening", "Sparkling", "Prospector's", "Great", "Rugged", "Rustic", "Bustling", "Excellent", "Sturdy", "Fortified", "Waxed", "Tempered", "Honored", "Molten", "Hyper", "Frosted", "Burning", "Flaky", "Stained", "Icy", "Faceted", "Exquisite", "Thiccc", "Charitable", "Coldfused", "Smoldering", "Automaton", "Dullish", "Safeguarded", "Edible", "Undead", "Horrendous", "Oasis", "Luckier", "Phantom", "Shiny", "Clownfish", "Shark", "Spongy", "Silly", "Dopey", "Waxy", "Luminous", "Luxurious", "Tiered", "Chipper", "Corrupted", "Dangerous", "Menacing", "Stellar", "Jaded", "Snowy", "Wither", "Slimy", "Bonkers", "Frosty", "Vicious", "Moonglow", "Zestful", "Vibrant", "Royal", "Blood-Soaked", "Double-Bit"]
        
        for prefix in prefixes:
            if item_name.startswith(prefix + " "):
                item_name = item_name[len(prefix) + 1:]
                break
        
        item_name = item_name.split("[")[0].strip()
        item_name = ''.join(char for char in item_name if char not in '✪➊➋➌➍➎')
        return item_name.strip()

    def filter_auctions(self, auctions):
        return [
            auction for auction in auctions
            if (self.is_active_bin_auction(auction) and
                auction.get("starting_bid", 0) <= self.params["max_buy_price"] and
                "attribute shard" not in auction.get("item_name", "").lower())
        ]

    def find_best_flip(self):
        all_auctions = self.auction_fetcher.fetch_all_auctions()
        filtered_auctions = sorted(self.filter_auctions(all_auctions), key=lambda x: random.random())

        item_groups = defaultdict(list)
        for auction in filtered_auctions:
            clean_item_name = self.get_clean_item_name(auction["item_name"])
            item_groups[clean_item_name].append(auction)

        best_flip = None
        best_profit = 0

        for clean_item_name, auctions in item_groups.items():
            if len(auctions) < self.params["min_sales_volume"]:
                continue

            sorted_auctions = sorted(auctions, key=lambda x: x["starting_bid"])
            lowest_auction = sorted_auctions[0]
            second_lowest_price = sorted_auctions[1]["starting_bid"] if len(sorted_auctions) > 1 else float('inf')

            potential_profit = second_lowest_price - lowest_auction["starting_bid"]
            profit_margin = (potential_profit / lowest_auction["starting_bid"]) * 100

            if (potential_profit >= self.params["min_profit"] and
                profit_margin >= self.params["threshold_percentage"] and
                profit_margin <= self.params["max_profit_margin"] and
                potential_profit > best_profit):

                best_profit = potential_profit
                best_flip = {
                    "item": lowest_auction["item_name"],
                    "clean_item_name": clean_item_name,
                    "lowest_price": lowest_auction["starting_bid"],
                    "second_lowest_price": second_lowest_price,
                    "potential_profit": potential_profit,
                    "profit_margin": profit_margin,
                    "auction_id": lowest_auction["uuid"],
                    "sales_volume": len(auctions)
                }

        if best_flip:
            # Check against 3-day average
            price_data = self.price_fetcher.fetch_price_data(best_flip["clean_item_name"])
            if price_data and "three_day_avg_lowest_bin" in price_data:
                three_day_avg = price_data["three_day_avg_lowest_bin"]
                if best_flip["second_lowest_price"] > three_day_avg * 1.2:  # Price is 20% higher than 3-day average
                    logging.info(f"Flip for {best_flip['clean_item_name']} rejected due to inflated price compared to 3-day average.")
                    return None
                best_flip["three_day_avg"] = three_day_avg
            else:
                logging.warning(f"Could not fetch 3-day average for {best_flip['clean_item_name']}.")

        return best_flip

def print_flip_info(flip):
    print(f"\nBest flip found at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
    print(f"Item: {flip['item']}")
    print(f"Clean Item Name: {flip['clean_item_name']}")
    print(f"Lowest price: {flip['lowest_price']:,}")
    print(f"Second lowest price: {flip['second_lowest_price']:,}")
    if 'three_day_avg' in flip:
        print(f"3-day average lowest BIN: {flip['three_day_avg']:,.2f}")
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
    print("Starting Hypixel BIN Flip Calculator (Continuous Mode)...")

    params = {
        "threshold_percentage": float(input("Enter the minimum price difference threshold (default 20%): ") or 20),
        "min_profit": int(input("Enter the minimum profit in coins (default 10000): ") or 10000),
        "max_buy_price": int(input("Enter the maximum buy price in coins (default 1000000): ") or 1000000),
        "max_profit_margin": float(input("Enter the maximum profit margin percentage (default 50%): ") or 50),
        "min_sales_volume": int(input("Enter the minimum sales volume (default 5): ") or 5)
    }

    flip_finder = FlipFinder(params)

    print("\nStarting continuous flip search. Press Ctrl+C to stop.")

    last_flip_time = 0

    try:
        while True:
            current_time = time.time()
            if current_time - last_flip_time >= REFRESH_INTERVAL:
                print(f"\nFetching auctions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
                best_flip = flip_finder.find_best_flip()
                if best_flip:
                    print_flip_info(best_flip)
                    winsound.Beep(1000, 500)  # Beep when a flip is found
                    last_flip_time = current_time
                else:
                    print("No suitable flips found.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping the flip calculator. Thank you for using!")

if __name__ == "__main__":
    main()