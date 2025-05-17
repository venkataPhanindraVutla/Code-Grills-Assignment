"""
Telegram .onion Link Extractor

This script connects to a specified Telegram channel using the Telethon library,
extracts messages, and searches for .onion links within those messages.
The extracted links are then saved to a JSON file.
"""

import asyncio
import re
import json
import os
from datetime import datetime
from telethon import TelegramClient
from dotenv import load_dotenv
import logging

# Regex to find .onion links
ONION_REGEX = re.compile(r'http[s]?://[a-z0-9]{16,56}\.onion')
OUTPUT_FILE = 'onion_links.json'
LOG_FILE = 'extractor.log'

def setup_logging():
    """Configures logging for the script."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler(LOG_FILE),
                            logging.StreamHandler()
                        ])

def load_config(env_path='.env'):
    """Loads configuration from a .env file."""
    load_dotenv(env_path)
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    if not all([api_id, api_hash]):
        raise ValueError("Missing API_ID or API_HASH in .env file.")

    return int(api_id), api_hash

async def connect_telegram(api_id: int, api_hash: str):
    """Connects to the Telegram API."""
    client = TelegramClient('anon', api_id, api_hash)
    await client.start()
    if not await client.is_user_authorized():
        logging.info("Please run the script once to authorize your Telegram account.")
        raise ConnectionError("User not authorized. Please run manually first to log in.")
    return client

async def get_channel_entity(client: TelegramClient, channel_username: str):
    """Gets the channel entity from the username or ID."""
    logging.info(f"Connecting to channel: {channel_username}")
    try:
        entity = await client.get_entity(channel_username)
        logging.info("Connected successfully.")
        return entity
    except ValueError:
        logging.error(f"Error: Could not find channel '{channel_username}'. Please check the username or ID.")
        return None
    except Exception as e:
        logging.error(f"An error occurred while connecting to the channel: {e}")
        return None

async def extract_onion_links(client: TelegramClient, entity, channel_username: str, limit: int = 100):
    """Extracts .onion links from channel messages."""
    extracted_links = []
    logging.info("Fetching messages...")
    async for message in client.iter_messages(entity, limit=limit):
        if message.text:
            found_links = ONION_REGEX.findall(message.text)
            for link in found_links:
                link_data = {
                    "source": "telegram",
                    "url": link,
                    "discovered_at": datetime.utcfromtimestamp(message.date.timestamp()).isoformat() + 'Z',
                    "context": f"Found in Telegram channel @{channel_username}",
                    "status": "pending"
                }
                extracted_links.append(link_data)
    logging.info(f"Found {len(extracted_links)} .onion links.")
    return extracted_links

def save_links_to_json(links: list, output_file: str):
    """Saves extracted links to a JSON file."""
    with open(output_file, 'w') as f:
        for link_data in links:
            f.write(json.dumps(link_data) + '\n')
    logging.info(f"Extracted links saved to {output_file}")

async def main():
    """Main function to run the Telegram onion link extractor."""
    setup_logging()
    try:
        api_id, api_hash = load_config()
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return

    channel_username = input("Enter the Telegram channel username or ID: ")
    if not channel_username:
        logging.error("Channel username or ID cannot be empty.")
        return

    client = None
    try:
        client = await connect_telegram(api_id, api_hash)
        logging.info("Connected to Telegram API.")
        entity = await get_channel_entity(client, channel_username)
        logging.info(f"entity: {entity}")
        logging.info("Fetching messages from channel...")
        if entity:
            extracted_links = await extract_onion_links(client, entity, channel_username)
            save_links_to_json(extracted_links, OUTPUT_FILE)
    except ConnectionError as e:
        logging.error(f"Connection error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        if client and client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
