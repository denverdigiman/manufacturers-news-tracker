# Manufacturers News Tracker

A Python script that monitors the newsrooms and press release pages of key storage and data management vendors, automatically detecting and classifying new articles since the last run.

## What It Does

Each time the script runs it:

1. Checks the official newsroom RSS feeds for each tracked vendor via Google News
2. Checks Blocks & Files (blocksandfiles.com), a storage industry news site, filtering for articles that mention a tracked vendor by name in the title
3. Compares results against previously seen articles to identify only what is new
4. Fetches each new article and uses the Claude AI API to classify it into one of five categories: **New Product**, **New Feature**, **Partnership**, **Financial**, or **Other**
5. Updates the JSON state file and all CSV and Excel output files

## Tracked Vendors

- NetApp
- Pure (Pure Storage / Everpure)
- Rubrik
- Cohesity
- Commvault
- Veeam

## Output Files

All output files are written to the configured output directory.

| File | Description |
|------|-------------|
| `newsroom_seen_articles.json` | State file tracking all previously seen articles. Do not delete this unless you want to reset the baseline. |
| `newsroom_articles.csv` | Full snapshot of every article ever seen. Overwritten on every run. |
| `newsroom_articles.xlsx` | Full snapshot of every article ever seen in Excel format. One tab per vendor, sorted newest first. Overwritten on every run. |
| `newsroom_new_articles.csv` | Running log of newly discovered articles only. Appended to on every run. |
| `newsroom_new_articles.xlsx` | Running log of newly discovered articles only in Excel format. Single sheet, all vendors combined, newest entries at the top. Appended to on every run. |

## Column Layout

All CSV and Excel files use the following column layout:

```
source | data source | date | category | title | url
```

- **source** — the vendor name (e.g. NetApp, Veeam)
- **data source** — where the article was found: `Google` or `Blocks and Files`
- **date** — publication date in YYYY-MM-DD format
- **category** — AI-assigned classification: New Product, New Feature, Partnership, Financial, or Other
- **title** — article headline
- **url** — link to the full article

## Excel Formatting

Both `.xlsx` files share the same formatting:

- **Bold, light blue column headers**
- **Auto-sized columns** (capped at 80 characters wide)
- **Clickable hyperlinks** in the URL column

### newsroom_articles.xlsx
One worksheet (tab) per vendor, named after the vendor. Articles sorted newest to oldest within each tab. The file is completely regenerated on every run, always reflecting the full current state.

### newsroom_new_articles.xlsx
A single worksheet named "New Articles" containing all vendors combined. New articles are appended to the sheet on each run, with the most recently discovered articles at the top of each batch.

## Requirements

### Python Dependencies

```bash
pip3 install requests anthropic openpyxl
```

### API Key

The script uses the Claude API to classify articles. You will need an Anthropic API key set as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

To set this permanently so it is available every time you open a terminal, add it to your shell profile:

```bash
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zprofile
source ~/.zprofile
```

You can obtain an API key at [console.anthropic.com](https://console.anthropic.com).

## Usage

### Basic run (no date filter)
```bash
python3 manufacturers_news_tracker.py
```

### Only report articles from the last N days
```bash
python3 manufacturers_news_tracker.py --days 30
```

### Only report articles published on or after a specific date
```bash
python3 manufacturers_news_tracker.py --since 2026-01-01
```

### Show available options
```bash
python3 manufacturers_news_tracker.py --help
```

## First Run Behaviour

On the first run, the script saves all currently visible articles as a baseline without reporting any of them as new. This prevents a flood of historical articles being flagged. Run the script a second time to begin detecting genuinely new articles.

## Adding or Removing Vendors

Edit the `SOURCES` list near the top of the script. Each entry requires a `name` (display label) and a `query` (Google News search query using a `site:` filter pointing to the vendor's newsroom URL):

```python
SOURCES = [
    {
        "name":  "NetApp",
        "query": "site:netapp.com/newsroom/press-releases",
    },
    # Add more vendors here
]
```

## Scheduling Automatic Runs

To have the script run automatically on a schedule, add a cron job. For example, to run every weekday morning at 8 AM:

```bash
crontab -e
```

Add this line:

```
0 8 * * 1-5 export ANTHROPIC_API_KEY="your-key-here" && /usr/bin/python3 /Users/rick/manufacturers-news-tracker/manufacturers_news_tracker.py >> /Users/rick/manufacturers-news-tracker/tracker.log 2>&1
```

## Notes

- Google News RSS feeds do not provide a complete historical archive. They typically return the most recent 20–50 articles per query, and results can vary between runs. Using the `--days` flag is recommended to filter out older articles that occasionally surface in the feed.
- The Blocks & Files feed filters articles by checking whether a vendor name appears in the article title. Because "Pure" is a short common word, occasional false matches are possible for that vendor.
- Article classification requires an active internet connection and a valid Anthropic API key. If classification fails for any article, the category will be recorded as `Unknown`.
- Existing articles in the JSON state file from runs prior to classification being added will have an empty category field.
