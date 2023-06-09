# SINS: Stock Info Scraper

## Instructions

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

1. Install postgres:

```
sudo apt-get install postgresql postgresql-contrib
```

2. Now create a superuser for PostgreSQL

```
sudo -u postgres createuser --superuser name_of_user
```

3. And create a database using created user account

```
sudo -u name_of_user createdb name_of_database
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
