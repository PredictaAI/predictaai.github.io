import requests
import time
from typing import Dict, List, Optional

class BinanceNewsAPI:
    def get_announcements(self, limit: int = 10) -> List[Dict]:
        """
        Get latest announcements from Binance using the verified working endpoint
        """
        try:
            url = "https://www.binance.com/bapi/composite/v1/public/bulletin/getBulletinList"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            }
            
            payload = {
                "page": 1,
                "pageSize": limit,
                "lang": "en-US",
                "category": "announcement"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('list', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Binance announcements: {e}")
            print(f"Response status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            print(f"Response text: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            return []

    def get_new_listings(self, limit: int = 5) -> List[Dict]:
        """
        Get new crypto listing announcements
        """
        try:
            url = "https://www.binance.com/bapi/composite/v1/public/bulletin/getBulletinList"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            }
            
            payload = {
                "page": 1,
                "pageSize": limit,
                "lang": "en-US",
                "category": "new_crypto"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('list', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching new listings: {e}")
            return []

def format_announcements(items: List[Dict]) -> None:
    """Format and print announcement data"""
    if not items:
        print("No items found")
        return

    for item in items:
        print("\n" + "="*80)
        print(f"Title: {item.get('title', 'N/A')}")
        if 'publishTime' in item:
            print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['publishTime']/1000))}")
        if item.get('summary'):
            print(f"Summary: {item['summary'][:200]}...")
        print(f"URL: {item.get('url', 'N/A')}")

# Usage example
if __name__ == "__main__":
    binance_news = BinanceNewsAPI()
    
    print("\nLatest Binance Announcements:")
    announcements = binance_news.get_announcements(limit=5)
    format_announcements(announcements)
    
    print("\nLatest New Crypto Listings:")
    listings = binance_news.get_new_listings(limit=3)
    format_announcements(listings)
