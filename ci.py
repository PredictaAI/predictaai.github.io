import os
import yaml
import requests
from datetime import datetime
from openai import OpenAI
from pathlib import Path
import shutil
from typing import Dict, List, Optional
import logging

class CryptoNewsProcessor:
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        api_key = self.openai_api_key
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.cryptopanic_base_url = "https://cryptopanic.com/api/free/v1/posts/"
        self.cryptopanic_api_key = ""  # Replace with actual key
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('crypto_news_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_coingecko_news(self, token: str) -> List[Dict]:
        """Fetch news from CoinGecko API."""
        url = f"{self.coingecko_base_url}/news"
        params = {"filter": token}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])[:10]  # Get first 10 news items
        return []

    def get_cryptopanic_news(self, token: str) -> List[Dict]:
        """Fetch news from CryptoPanic API."""
        params = {
            "auth_token": self.cryptopanic_api_key,
            "currencies": token,
            "kind": "news"
        }
        response = requests.get(self.cryptopanic_base_url, params=params)
        print(response)
        if response.status_code == 200:
            return [news for news in response.json().get("results", []) 
                   if news["kind"] == "news"]
        return []

    def get_sentiment_and_summary(self, title: str, description: str) -> tuple:
        """Get sentiment and summary from OpenAI API."""
        try:
            # Get summary
            summary_prompt = f"Summarize this title in exactly 5 words: {title}"
            client = OpenAI(api_key = self.openai_api_key)
            summary_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": summary_prompt}]
            )
            five_word_summary = summary_response.choices[0].message.content.strip()

            # Get sentiment
            sentiment_prompt = f"""Analyze the sentiment of this news article. Title: {title}
            Description: {description}
            Respond with exactly one of these: Very Bullish, Bullish, Neutral, Bearish, Very Bearish"""
            
            sentiment_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": sentiment_prompt}]
            )
            sentiment = sentiment_response.choices[0].message.content.strip()

            # Map sentiment to YAML format
            sentiment_mapping = {
                "Very Bullish": "VeryBullish",
                "Very Bearish": "VeryBearish"
            }
            formatted_sentiment = sentiment_mapping.get(sentiment, sentiment)

            return five_word_summary, formatted_sentiment
        except Exception as e:
            print(f"Error in OpenAI API call: {e}")
            return "Error generating summary", "Neutral"

    def generate_and_save_image(self, prompt: str, save_path: str) -> str:
        """Generate image using DALL-E with detailed error logging."""
        try:
            self.logger.info(f"Attempting to generate image with prompt: {prompt}")
            client = OpenAI(api_key = self.openai_api_key)
            
            # List available models
            models = client.models.list()
            self.logger.debug(f"Available OpenAI models: {models}")
            
            # Try DALL-E 3 first, fall back to DALL-E 2 if needed
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=f"Create a professional financial chart or visualization related to: {prompt}. Style: Modern, clean, financial.",
                    n=1,
                    size="1024x1024"
                )
            except Exception as e:
                self.logger.warning(f"DALL-E 3 failed, trying DALL-E 2: {str(e)}")
                response = client.images.generate(
                    model="dall-e-2",
                    prompt=f"Create a professional financial chart or visualization related to: {prompt}. Style: Modern, clean, financial.",
                    n=1,
                    size="1024x1024"
                )
            
            self.logger.debug(f"OpenAI image generation response: {response}")
            
            image_url = response.data[0].url
            self.logger.info(f"Successfully generated image URL: {image_url}")
            
            # Download and save image
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    img_response.raw.decode_content = True
                    shutil.copyfileobj(img_response.raw, f)
                self.logger.info(f"Successfully saved image to: {save_path}")
                return save_path
            else:
                self.logger.error(f"Failed to download image. Status code: {img_response.status_code}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error in image generation: {str(e)}")
            self.logger.error(f"Error details: {e}")
            return ""

    def generate_and_save_image_old(self, title: str, save_path: str) -> str:
        """Generate image using OpenAI and save it."""
        client = OpenAI(api_key = self.openai_api_key)
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=f"Create a chart or visualization related to: {title}",
                n=1,
                size="1024x1024"
            )
            image_url = response['data'][0]['url']
            
            # Download and save image
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                with open(save_path, 'wb') as f:
                    img_response.raw.decode_content = True
                    shutil.copyfileobj(img_response.raw, f)
            return save_path
        except Exception as e:
            print(f"Error generating image: {e}")
            return ""

    def process_news(self, token: str):
        """Main function to process news and update YAML files."""
        # Create base directory path
        current_date = datetime.now().strftime("%m%d%Y")
        base_dir = f"news/{token}-USDT/{current_date}"
        os.makedirs(base_dir, exist_ok=True)
        
        yaml_path = os.path.join(base_dir, "predictions.yaml")
        
        # Initialize or load existing YAML
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f) or {"predictions": []}
            current_id = max([p['id'] for p in data['predictions']], default=0)
        else:
            data = {"predictions": []}
            current_id = 0

        # Process CoinGecko news
        coingecko_news = self.get_coingecko_news(token)
        for news in coingecko_news:
            current_id += 1
            
            # Create directory for images
            img_dir = os.path.join(base_dir, str(current_id))
            os.makedirs(img_dir, exist_ok=True)
            
            # Process news item
            summary, sentiment = self.get_sentiment_and_summary(
                news['title'], news['description']
            )
            
            # Generate and save image
            image_path = os.path.join(img_dir, "chart.png")
            self.generate_and_save_image(news['title'], image_path)
            
            # Create news entry
            news_entry = {
                "id": current_id,
                "title": f"{news['news_site']} - {sentiment}",
                "preview": summary,
                "fullContent": news['description'],
                "image": f"news/{token}-USDT/{current_date}/{current_id}/chart.png",
                "sourcelink": news['url'],
                "sentiment": sentiment
            }
            
            data['predictions'].append(news_entry)

        # Process CryptoPanic news
        cryptopanic_news = self.get_cryptopanic_news(token)
        for news in cryptopanic_news:
            current_id += 1
            
            # Create directory for images
            img_dir = os.path.join(base_dir, str(current_id))
            os.makedirs(img_dir, exist_ok=True)
            
            # Process news item
            summary, sentiment = self.get_sentiment_and_summary(
                news['title'], news['title']  # Using title as description
            )
            
            # Generate and save image
            image_path = os.path.join(img_dir, "chart.png")
            self.generate_and_save_image(news['title'], image_path)
            
            # Create news entry
            news_entry = {
                "id": current_id,
                "title": f"{news['domain']} - {sentiment}",
                "preview": summary,
                "fullContent": news['title'],
                "image": f"news/{token}-USDT/{current_date}/{current_id}/chart.png",
                "sourcelink": news['url'],
                "sentiment": sentiment
            }
            
            data['predictions'].append(news_entry)

        # Save updated YAML file
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)

def main():
    openai_api_key = ""  # Replace with actual key
    processor = CryptoNewsProcessor(openai_api_key)
    
    # Process news for both BTC and ETH
    for token in ["BTC"]:
        try:
            processor.process_news(token)
            print(f"Successfully processed news for {token}")
        except Exception as e:
            print(f"Error processing {token} news: {e}")

if __name__ == "__main__":
    main()
