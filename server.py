from flask import Flask, jsonify, send_from_directory, render_template
import sqlite3
import os

app = Flask(__name__)
DB_NAME = "demo_data.db"
IMAGE_FOLDER = "demo_images"

def image_url(image_path):
    """URL for a saved image, or None. The scraper stores error text such as "Image Too Small" here."""
    filename = os.path.basename((image_path or "").replace("\\", "/"))
    if filename and os.path.isfile(os.path.join(IMAGE_FOLDER, filename)):
        return f"/images/{filename}"
    return None

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

# 1. THE FRONTEND ROUTE
# When you go to localhost:5000, this loads the HTML page
@app.route('/')
def home():
    return render_template('index.html')

# 2. THE API ROUTE
# The frontend calls this to get the raw data (JSON)
@app.route('/api/news')
def api_news():
    # No database until the scraper has run: an empty feed, not a crash
    if not os.path.exists(DB_NAME):
        return jsonify([])

    conn = get_db_connection()
    # Get latest 50 articles
    articles = conn.execute('SELECT * FROM articles ORDER BY date_added DESC LIMIT 50').fetchall()
    conn.close()
    
    # Convert database rows to a clean list for the frontend
    news_list = []
    for row in articles:
        news_list.append({
            'id': row['id'],
            'heading': row['heading'],
            'category': row['category'],
            'body': row['body_text'][:200] + ("..." if len(row['body_text']) > 200 else ""), # Show only preview text
            'image_url': image_url(row['image_path']),
            'original_url': row['url'],
            'date': row['date_added']
        })
        
    return jsonify(news_list)

# 3. THE IMAGE ROUTE
# This serves the actual image files from your local folder
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    print("🚀 Server running at http://127.0.0.1:5000")
    # debug=True would let anyone who reaches the port run code through the Werkzeug debugger
    app.run(port=5000)
