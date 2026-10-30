# Aviation News Engine

A Python-based news aggregator designed to scrape, store, and serve aviation-related news from various sources.

## Features

- **News Scraper**: Automatically fetches latest articles from aviation websites defined in `sites.json`.
- **Data Persistence**: Stores scraped articles in a local SQLite database (`demo_data.db`), created when you first run the scraper. It isn't in this repo because the articles belong to their publishers.
- **Web Interface**: Includes a lightweight web server to browse and read the collected news in a user-friendly format.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DushyantRajpurohit/Aviation-News-Engine.git
   cd Aviation-News-Engine
   ```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

1. **Run the Scraper**

Fetch the latest news and update the database:
```bash
python demo_engine.py
```

2. **Start the Web Server**

Launch the application to view the news:
```bash
python server.py
```
Access the interface in your browser (typically at http://127.0.0.1:5000).

3. **Utilities & Configuration**

- **Add/Remove Sites**: Edit `sites.json` to configure the target websites and scraping rules.
- **Inspect Data**: Use the utility script to check database contents:

```bash
python view_data.py
```

## Project Structure

- `server.py`: Main entry point for the web application.
- `demo_engine.py`: Core logic for scraping news sites.
- `sites.json`: Configuration file for target URLs.
- `demo_data.db`: SQLite database storing the news data (created by the scraper, not committed).
- `test_app.py`: Tests for categorisation and the news API (`pytest`).
- `templates/`: HTML templates for the web interface.
