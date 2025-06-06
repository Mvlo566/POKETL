# POKETL

**POKETL** is a Python toolkit designed to automate the scraping, analysis, and injection of Pokémon tournament data (from LimitlessTCG) into a PostgreSQL database.  
The project features a terminal interface with an animated (ASCII/Pikachu) menu to run all processing scripts with a single click.

## 🚀 Main Features

- Automated scraping of Pokémon tournaments on LimitlessTCG: decklists, players, results, etc.
- Transformation of raw data into structured JSON files, ready for insertion.
- Optimized and sequential PostgreSQL injection (cards, players, tournaments, matches, decklists, results).
- Animated terminal interface to manage all processes.
- Detailed logging and real-time progress tracking for each step.
- Modular organization: each script is standalone and can be run individually or via the launcher.  
  ⚠️ **Note**: Some tables depend on others, so the execution order matters.

---

## 📦 Project Structure

```
.
├── launcher.py           # Launches the animated terminal interface (main menu)
├── scripts/              # All insertion and utility scripts
│   ├── scraping\_tournaments.py     # Scraping LimitlessTCG → JSON
│   ├── insert\_wrk\_cards.py         # Insert cards into PostgreSQL
│   ├── insert\_wrk\_players.py       # Insert players
│   ├── insert\_wrk\_tournaments.py   # Insert tournaments
│   ├── insert\_wrk\_matches.py       # Insert matches
│   ├── insert\_wrk\_decklists.py     # Insert decklists
│   └── insert\_wrk\_results.py       # Insert results
├── GIF/
│   └── pikachu\_loading.gif # ASCII/GIF animations for the UI
├── sample\_output/        # Generated JSON files
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (PostgreSQL connection)
````
---
## 🚦 Quick Start
1. **Clone the repository**
    ```bash
    git clone https://github.com/Mvlo566/POKETL.git
    cd POKETL
    ```
2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Configure PostgreSQL connection**  
    Fill in the `.env` file with your database settings (host, user, password, etc.).
4. **Launch the terminal interface**
    ```bash
    python launcher.py
    ```
5. **Or run a specific script**
    ```bash
    python scripts/insert_wrk_players.py
    ```
---
## 💾 Main Dependencies
- `aiohttp`
- `beautifulsoup4`
- `blessed`
- `lxml`
- `pandas`
- `pillow`
- `psycopg2`
- `python-dotenv`
- `requests`
---
## 📝 Notes & Recommendations
- **Insertion script order**:  
  `insert_wrk_cards.py` → `insert_wrk_decklists.py` → `insert_wrk_tournaments.py` →  
  `insert_wrk_players.py` → `insert_wrk_matches.py` → `insert_wrk_results.py`
- **Logging**: All scripts output real-time logs and errors.
- **Modular**: Each script can be rerun individually. Re-running = incremental update (no overwrite).
- **The `launcher.py`** manages everything through an ASCII menu.
---
# ODBC Driver Setup
## Step 1
- Install PostgreSQL ODBC Driver  
  https://www.postgresql.org/ftp/odbc/releases/  
- Version used: `REL-17_00_0005`  
- Install PostgreSQL
## Step 2
- Open the ODBC manager  
- On Windows, search for:  
  **"ODBC Data Sources"**
## Step 3
- Under **"User DSN"**  
- Click on **"Add..."**  
- In **"Create a New Data Source"**  
- Select **"PostgreSQL Unicode"**  
- Enter the following settings:
```

```
## Step 4
- Register in the **ODBC Driver**
- Fill in the following credentials:


```
## The connection is successful 🎉