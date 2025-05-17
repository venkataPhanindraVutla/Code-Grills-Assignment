import asyncio
import aiohttp
import json
import re
import logging
from datetime import datetime, timezone

# Configuration
PASTEBIN_ARCHIVE_URL = "https://pastebin.com/archive"
PASTEBIN_RAW_URL = "https://pastebin.com/raw/{}"
KEYWORDS = ["crypto", "bitcoin", "ethereum", "blockchain", "t.me"]
OUTPUT_FILE = "keyword_matches.jsonl"
LOG_FILE = "crawler.log"
REQUEST_DELAY = 1 # Seconds to wait between fetching paste content

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler()
                    ])

async def get_paste_ids(url):
    """
    Scrapes the Pastebin archive page to extract paste IDs asynchronously.
    Returns a list of paste IDs.
    """
    logging.info(f"Fetching paste IDs from {url}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status() # Raise an exception for bad status codes
                text = await response.text()
                # Simple regex to find paste IDs in the archive HTML
                # This might need adjustment based on Pastebin's HTML structure
                paste_ids = re.findall(r'/([a-zA-Z0-9]{8})', text)
                # Get the latest 30 unique IDs
                unique_ids = list(dict.fromkeys(paste_ids))[:30]
                logging.info(f"Found {len(unique_ids)} paste IDs.")
                return unique_ids
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching paste IDs: {e}")
        return []

async def get_paste_content(session, paste_id):
    """
    Fetches the raw content of a paste given its ID asynchronously.
    Returns the paste content as a string, or None if an error occurs.
    """
    url = PASTEBIN_RAW_URL.format(paste_id)
    logging.info(f"Fetching content for paste ID {paste_id} from {url}...")
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            logging.info(f"Successfully fetched content for paste ID {paste_id}.")
            return await response.text()
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching content for paste ID {paste_id}: {e}")
        return None

async def find_keywords(content, keywords):
    """
    Checks if any of the specified keywords are present in the content asynchronously.
    Returns a list of found keywords.
    """
    found = []
    if content:
        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                found.append(keyword)
    await asyncio.sleep(0)
    return found

async def create_json_entry(paste_id, keywords_found):
    """
    Creates a JSON object for a paste with found keywords asynchronously.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    await asyncio.sleep(0)
    return {
        "source": "pastebin",
        "context": f"Found relevant content in Pastebin paste ID {paste_id}",
        "paste_id": paste_id,
        "url": PASTEBIN_RAW_URL.format(paste_id),
        "discovered_at": now_utc,
        "keywords_found": keywords_found,
        "status": "pending"
    }

async def process_paste(session, paste_id):
    """
    Fetches content, finds keywords, and creates a JSON entry for a single paste asynchronously.
    Returns the JSON entry if keywords are found, otherwise None.
    Includes a delay to respect rate limits.
    """
    content = await get_paste_content(session, paste_id)
    if content:
        keywords_found = await find_keywords(content, KEYWORDS)
        if keywords_found:
            logging.info(f"Keywords {keywords_found} found in paste ID {paste_id}.")
            return await create_json_entry(paste_id, keywords_found)
        else:
            logging.info(f"No keywords found in paste ID {paste_id}.")

    # Add a delay between processing pastes
    await asyncio.sleep(REQUEST_DELAY)
    return None

async def main():
    """
    Main function to orchestrate the scraping and keyword checking process as an asynchronous pipeline.
    """
    logging.info("Starting Pastebin Keyword Crawler...")

    # Step 1: Get paste IDs
    paste_ids = await get_paste_ids(PASTEBIN_ARCHIVE_URL)

    if not paste_ids:
        logging.info("No paste IDs found. Exiting.")
        return

    logging.info(f"Processing {len(paste_ids)} pastes asynchronously with a delay of {REQUEST_DELAY} seconds...")

    # Step 2 & 3: Process each paste concurrently and find keywords
    matches = []
    async with aiohttp.ClientSession() as session:
        for paste_id in paste_ids:
            result = await process_paste(session, paste_id)
            if result:
                matches.append(result)

    # Step 4: Save matches
    if matches:
        logging.info(f"Saving {len(matches)} matches to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w') as f: # Use 'w' to overwrite or create
            for match in matches:
                json.dump(match, f)
                f.write('\n')
        logging.info("Matches saved.")
    else:
        logging.info("No matches found to save.")

    # Step 5: Notify completion
    logging.info("Pastebin Keyword Crawler finished.")

if __name__ == "__main__":
    asyncio.run(main())
