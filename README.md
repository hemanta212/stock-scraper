# S-IN-S: Stock Info Scraper
<!-- [![Build](https://github.com/Stockinerary/thc_beh_2023_hemanta/actions/workflows/main.yml/badge.svg)](https://github.com/Stockinerary/thc_beh_2023_hemanta/actions/workflows/main.yml)-->
[![Tests](https://github.com/Stockinerary/thc_beh_2023_hemanta/actions/workflows/tests.yml/badge.svg)](https://github.com/Stockinerary/thc_beh_2023_hemanta/actions/workflows/tests.yml)

Scrapes the stock information off the YahooAPI and StockAnalysis.com.

- Supports SQLITE and PostgresQL database and allows exporting to CSVs

- The Scraping Job runs every 6 hours here on github actions, saves to remote postgres and sqlite databases.

- The postgresql database is hosted live at custom azure vps @ v.hemantasharma.com.np

- You can obtain the build artifacts of `data.csv` and `database.sqlite` in releases section.

## Instructions for local installation

- Clone this repository

```bash
cd Stock-Scraper
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
playwright install
python main.py
```

Sqlite db output will be created at data directory in current folder

## Setting up Postgresql Database [Optional]

1. Install postgres client and server:

```
sudo apt-get install postgresql postgresql-contrib postgresql-client
```

2. Start the postgres service

```
sudo service postgresql start
```

3. Login to the psql shell

```
sudo -i -u postgres psql
```

2. Now create a user and password

```
CREATE USER sammy WITH PASSWORD 'password';
```

NOTE: Don't forget the `;` semicolon, You should see the output `CREATE ROLE`

3. And create a database using created user account

```
CREATE DATABASE sammydb OWNER sammy;
```

4. Quit the psql shell

```
\q
```

4. You can access created database with created user by,

```
psql -U name_of_user -d name_of_database
```

5. Populate the `.env` file, Fill the dbname, username and password according to your above steps.

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=yourDbName
POSTGRES_USER=yourUserName
POSTGRES_PASSWORD=yourPassword
```

6. Run the script again.

```
python main.py
```

7. Exporting Postgres to csv

```
python export.py
```

CSV file will be created inside data folder.
