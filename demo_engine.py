import os
import re
import json
import requests
import sqlite3
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from newspaper import Article, build
from PIL import Image
from io import BytesIO

# --- CONFIGURATION ---
IMAGE_FOLDER = "demo_images"
DB_NAME = "demo_data.db"
TARGET_ARTICLES_PER_SITE = 10 
MAX_WORKERS = 10  # Scans 10 websites at the SAME time

# Database Lock prevents "Database is locked" errors during parallel writes
db_lock = threading.Lock()

CATEGORIES = {
    "Commercial": ["IndiGo", "Air India", "Delta", "United", "American Airlines", 
                   "Etihad", "Emirates", "Pakistan International", "Air New Zealand", 
                   "Ryanair", "passenger", "commercial", "airline", "scheduled"],
    "Defence": ["defence", "military", "air force", "fighter", "navy", "drdo", "iaf"],
    "MRO": ["maintenance", "repair", "overhaul", "technical", "engineering", "mro", "spare parts"],
    "Cargo": ["cargo", "freight", "logistics", "ground handling", "baggage"],
    "Business": ["private jet", "charter", "business jet", "corporate", "non-scheduled"],
}

# --- DATABASE SETUP ---
def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS articles
                     (id INTEGER PRIMARY KEY, 
                      url TEXT UNIQUE, 
                      heading TEXT, 
                      category TEXT,
                      body_text TEXT, 
                      image_path TEXT, 
                      date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

def content_exists(url, heading):
    """Thread-safe check for duplicates"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check URL
        cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        if cursor.fetchone():
            conn.close()
            return True

        # Check Headline
        cursor.execute("SELECT 1 FROM articles WHERE heading = ?", (heading,))
        if cursor.fetchone():
            conn.close()
            return True
            
        conn.close()
        return False

def save_to_db(url, heading, category, body, image_path):
    """Thread-safe write to database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO articles (url, heading, category, body_text, image_path) VALUES (?, ?, ?, ?, ?)",
                      (url, heading, category, body, image_path))
            conn.commit()
            print(f"   [Saved] [{category}] {heading[:40]}...") 
        except sqlite3.IntegrityError:
            pass
        conn.close()

# --- HELPER FUNCTIONS ---

def assign_category(text):
    """Pick the category with the most keyword hits, matching whole words only."""
    scores = {}
    for category, keywords in CATEGORIES.items():
        pattern = r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b"
        scores[category] = len(re.findall(pattern, text, re.IGNORECASE))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"

def download_image(image_url):
    if not image_url: return "No Image"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(image_url, headers=headers, stream=True, timeout=15)
        
        if response.status_code == 200:
            image_content = response.content
            
            if len(image_content) < 5 * 1024: 
                return "Image Too Small"

            try:
                img = Image.open(BytesIO(image_content))
                img.verify()
            except Exception:
                return "Image Corrupt"

            ext = "jpg"
            filename = f"{hashlib.md5(image_url.encode()).hexdigest()}.{ext}"
            filepath = os.path.join(IMAGE_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_content)
                
            return filepath
            
    except Exception:
        return "Image Download Error"
        
    return "Download Failed"

def process_website(site_url):
    print(f"🚀 Scanning: {site_url}")
    try:
        # memoize_articles=False is safer for updates, but keeping it True is faster if running frequently
        paper = build(site_url, memoize_articles=False)
    except Exception as e:
        print(f"❌ Connection failed: {site_url}")
        return

    articles_found = 0
    
    # We only look at the first 20 links to be fast, assuming news is at the top
    for article in paper.articles[:20]: 
        if articles_found >= TARGET_ARTICLES_PER_SITE:
            break

        try:
            # Quick Check 1: URL (Avoid download if URL is known)
            with db_lock:
                conn = sqlite3.connect(DB_NAME, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ?", (article.url,))
                exists = cursor.fetchone()
                conn.close()
            
            if exists:
                continue

            article.download()
            article.parse()
            
            if len(article.text) < 200: continue

            # Quick Check 2: Headline (Avoid duplicates from different URLs)
            if content_exists(article.url, article.title):
                continue

            final_category = assign_category(article.text)
            local_image = download_image(article.top_image)

            save_to_db(article.url, article.title, final_category, article.text, local_image)
            articles_found += 1

        except Exception:
            continue
    
    print(f"✅ Finished {site_url} (Added {articles_found} articles)")

# --- PARALLEL EXECUTION ---

def run_fast():
    print(f"--- ⚡ Starting High-Speed Extraction ---")
    
    try:
        with open('sites.json', 'r') as f:
            sites = json.load(f)
            
        # This is the Magic Line: It runs 10 sites at once
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(process_website, sites)
            
        print("\n✅ All sites processed.")
        
    except FileNotFoundError:
        print("❌ Error: sites.json missing.")

if __name__ == "__main__":
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    init_db()
    run_fast()
