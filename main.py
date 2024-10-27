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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('flip_finder.log')
    ]
)

# Constants
HYPIXEL_API_BASE_URL = "https://api.hypixel.net"
PRICE_API_BASE_URL = "http://195.201.18.228:5000/item"
API_KEY = "MazH2JtZeLCxIydNaWSaqHEpZvy3p1TS"

# Known generic item names to ignore
IGNORED_ITEMS = {
    "Helmet", "Chestplate", "Leggings", "Boots",
    "Sword", "Bow", "Rod", "Pickaxe", "Axe", "Shovel",
    "Hoe", "Shears", "Drill", "Generator"
}

class AuctionFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_page(self, page):
        try:
            response = self.session.get(f"{HYPIXEL_API_BASE_URL}/skyblock/auctions?page={page}", timeout=5)
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

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(self.fetch_page, page) for page in range(1, total_pages)]
            for future in as_completed(futures):
                page_data = future.result()
                if page_data:
                    all_auctions.extend(page_data.get("auctions", []))

        return all_auctions

class PriceFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.failed_items = set()  # Track items that failed price fetch

    def fetch_price_data(self, item_name):
        if item_name in self.failed_items or item_name in IGNORED_ITEMS:
            return None
            
        try:
            url = f"{PRICE_API_BASE_URL}/{API_KEY}/{item_name}"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.failed_items.add(item_name)  # Add to failed items set
            logging.debug(f"Error fetching price data for {item_name}: {e}")  # Changed to debug
            return None
        except requests.RequestException as e:
            logging.debug(f"Error fetching price data for {item_name}: {e}")  # Changed to debug
            return None

class FlipFinder:
    def __init__(self, params):
        self.params = params
        self.auction_fetcher = AuctionFetcher()
        self.price_fetcher = PriceFetcher()
        self.suggested_auctions = set()
        self.inflated_items = set()
        self.avg_price_rejected_items = set()
        self.last_scan_time = 0
        self.scan_cooldown = 1  # Minimum seconds between scans

    @staticmethod
    def is_active_bin_auction(auction):
        return (not auction.get("claimed", False) and
                auction.get("end", 0) > int(time.time() * 1000) and
                auction.get("bin", False) and
                auction.get("highest_bid_amount", 0) == 0)

    @staticmethod
    def get_clean_item_name(item_name):
        prefixes = ["Brilliant", "Deadly", "Robust", "Blended", "Lumberjack's", "Dimensional", 
                   "Greater Spook", "Lustrous", "Glacial", "Fanged", "Jerry's", "Gentle", 
                   "Odd", "Fast", "Fair", "Epic", "Sharp", "Heroic", "Spicy", "Legendary", 
                   "Dirty", "Fabled", "Suspicious", "Gilded", "Warped", "Withered", "Bulky", 
                   "Stellar", "Heated", "Ambered", "Fruitful", "Magnetic", "Fleet", "Mithraic", 
                   "Auspicious", "Refined", "Blessed", "Toil", "Bountiful", "Loving", "Ridiculous", 
                   "Necrotic", "Giant", "Empowered", "Ancient", "Sweet", "Moil", "Silky", "Bloody", 
                   "Shaded", "Precise", "Spiritual", "Headstrong", "Clean", "Fierce", "Heavy", 
                   "Light", "Perfect", "Neat", "Elegant", "Fine", "Grand", "Hasty", "Rapid", 
                   "Unreal", "Awkward", "Rich", "Spiked", "Renowned", "Cubic", "Reinforced", 
                   "Salty", "Treacherous", "Stiff", "Lucky", "Very", "Highly", "Extremely", 
                   "Absolutely", "Even More", "Smart", "Titanic", "Wise", "Strong", "Unstable", 
                   "Superior", "Pure", "Holy", "Candied", "Submerged", "Bizarre", "Mythic", 
                   "Strengthened", "Jaded", "Zealous", "Godly", "Demonic", "Forceful", "Hurtful", 
                   "Strong", "Unpleasant", "Keen", "Pretty", "Shiny", "Simple", "Strange", "Vivid", 
                   "Bizarre", "Itchy", "Ominous", "Pleasant", "Pretty", "Shiny", "Simple", "Strange", 
                   "Vivid", "Awful", "Lush", "Pitiful", "Raider's", "Refurbished", "Festive", 
                   "Green Thumb", "Rooted", "Blooming", "Earthy", "Mossy", "Milky", "Signature", 
                   "Unyielding", "Dirty", "Stranded", "Chomp", "Pitchin'", "Glistening", "Sparkling", 
                   "Prospector's", "Great", "Rugged", "Rustic", "Bustling", "Excellent", "Sturdy", 
                   "Fortified", "Waxed", "Tempered", "Honored", "Molten", "Hyper", "Frosted", 
                   "Burning", "Flaky", "Stained", "Icy", "Faceted", "Exquisite", "Thiccc", 
                   "Charitable", "Coldfused", "Smoldering", "Automaton", "Dullish", "Safeguarded", 
                   "Edible", "Undead", "Horrendous", "Oasis", "Luckier", "Phantom", "Shiny", 
                   "Clownfish", "Shark", "Spongy", "Silly", "Dopey", "Waxy", "Luminous", "Luxurious", 
                   "Tiered", "Chipper", "Corrupted", "Dangerous", "Menacing", "Stellar", "Jaded", 
                   "Snowy", "Wither", "Slimy", "Bonkers", "Frosty", "Vicious", "Moonglow", 
                   "Zestful", "Vibrant", "Royal", "Blood-Soaked", "Double-Bit"]
        
        # Remove fragment symbol and everything before it
        item_name = item_name.split('⚚')[-1].strip()
        
        for prefix in prefixes:
            if item_name.startswith(prefix + " "):
                item_name = item_name[len(prefix) + 1:]
                break
        
        item_name = item_name.split("[")[0].strip()
        item_name = ''.join(char for char in item_name if char not in '✪➊➋➌➍➎')
        return item_name.strip()

    def filter_auctions(self, auctions):
        filtered = []
        for auction in auctions:
            if not self.is_active_bin_auction(auction):
                continue
            
            if auction.get("starting_bid", 0) > self.params["max_buy_price"]:
                continue
            
            if "attribute shard" in auction.get("item_name", "").lower():
                continue
                
            clean_name = self.get_clean_item_name(auction["item_name"])
            
            # Skip generic items and previously rejected items
            if (clean_name in IGNORED_ITEMS or 
                clean_name in self.inflated_items or 
                clean_name in self.avg_price_rejected_items):
                continue
                
            filtered.append(auction)
        
        return filtered

    def find_best_flip(self):
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_cooldown:
            time.sleep(self.scan_cooldown - (current_time - self.last_scan_time))
        
        self.last_scan_time = current_time
        
        all_auctions = self.auction_fetcher.fetch_all_auctions()
        if not all_auctions:
            logging.error("Failed to fetch auctions. Retrying in next cycle.")
            return None
            
        filtered_auctions = self.filter_auctions(all_auctions)

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
            
            auction_key = (lowest_auction["auctioneer"], clean_item_name)
            if auction_key in self.suggested_auctions:
                continue

            second_lowest_price = float('inf')
            for auction in sorted_auctions[1:]:
                if self.get_clean_item_name(auction["item_name"]) == clean_item_name:
                    second_lowest_price = auction["starting_bid"]
                    break
            
            if second_lowest_price == float('inf'):
                second_lowest_price = sorted_auctions[1]["starting_bid"] if len(sorted_auctions) > 1 else float('inf')

            potential_profit = second_lowest_price - lowest_auction["starting_bid"]
            profit_margin = (potential_profit / lowest_auction["starting_bid"]) * 100

            if (potential_profit >= self.params["min_profit"] and
                profit_margin >= self.params["threshold_percentage"] and
                profit_margin <= self.params["max_profit_margin"]):

                price_data = self.price_fetcher.fetch_price_data(clean_item_name)
                if price_data and "three_day_avg_lowest_bin" in price_data:
                    three_day_avg = price_data["three_day_avg_lowest_bin"]
                    if second_lowest_price > three_day_avg * 1.2:
                        self.inflated_items.add(clean_item_name)
                        self.avg_price_rejected_items.add(clean_item_name)
                        logging.debug(f"Added {clean_item_name} to rejected items lists due to high price compared to 3-day average.")
                        continue
                else:
                    logging.debug(f"Could not fetch 3-day average for {clean_item_name}.")
                    continue

                if potential_profit > best_profit:
                    best_profit = potential_profit
                    best_flip = {
                        "item": lowest_auction["item_name"],
                        "clean_item_name": clean_item_name,
                        "lowest_price": lowest_auction["starting_bid"],
                        "second_lowest_price": second_lowest_price,
                        "three_day_avg": three_day_avg,
                        "potential_profit": potential_profit,
                        "profit_margin": profit_margin,
                        "auction_id": lowest_auction["uuid"],
                        "sales_volume": len(auctions),
                        "auctioneer": lowest_auction["auctioneer"]
                    }

        if best_flip:
            self.suggested_auctions.add((best_flip["auctioneer"], best_flip["clean_item_name"]))

        return best_flip

def print_flip_info(flip):
    print(f"\nBest flip found at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
    print(f"Item: {flip['item']}")
    print(f"Clean Item Name: {flip['clean_item_name']}")
    print(f"Lowest price: {flip['lowest_price']:,}")
    print(f"Second lowest price: {flip['second_lowest_price']:,}")
    print(f"3-day average lowest BIN: {flip['three_day_avg']:,.2f}")
    print(f"Potential profit: {flip['potential_profit']:,}")
    print(f"Profit margin: {flip['profit_margin']:.2f}%")
    print(f"Sales volume: {flip['sales_volume']}")
    print(f"Seller: {flip['auctioneer']}")

    command = f"/viewauction {flip['auction_id']}"
    pyperclip.copy(command)
    print(f"\nLowest BIN auction command copied to clipboard: {command}")
    print("Paste this command in-game to view the auction.")
    print("\nCAUTION: Always double-check prices before purchasing!")
    print("Consider checking external price sources for additional verification.")

def main():
    print("Starting Hypixel BIN Flip Calculator (Continuous Mode)...")

    params = {
        "threshold_percentage": 20,
        "min_profit": 1000000,
        "max_buy_price": 25000000,
        "max_profit_margin": 1000,
        "min_sales_volume": 10
    }

    flip_finder = FlipFinder(params)

    print("\nStarting continuous flip search. Press Ctrl+C to stop.")
    print("Logging to flip_finder.log for detailed debugging information.")
    
    consecutive_errors = 0
    max_consecutive_errors = 3
    error_cooldown = 30  # seconds

    try:
        while True:
            try:
                start_time = time.time()
                print(f"\nFetching auctions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
                best_flip = flip_finder.find_best_flip()
                
                if best_flip:
                    print_flip_info(best_flip)
                    winsound.Beep(1000, 500)  # Beep when a flip is found
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    print("No suitable flips found.")
                
                # Calculate remaining time for rate limiting
                elapsed_time = time.time() - start_time
                if elapsed_time < 1:
                    time.sleep(1 - elapsed_time)
                    
            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                logging.error(f"Network error occurred: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logging.warning(f"Too many consecutive errors. Cooling down for {error_cooldown} seconds...")
                    time.sleep(error_cooldown)
                    consecutive_errors = 0
                continue
                
            except Exception as e:
                logging.error(f"Unexpected error occurred: {e}")
                time.sleep(1)
                continue
                
    except KeyboardInterrupt:
        print("\nStopping the flip calculator. Thank you for using!")
    except Exception as e:
        logging.critical(f"Critical error occurred: {e}")
        raise

if __name__ == "__main__":
    main()