"""
Connects to postgresql db and export the data in csv format
"""
import csv
import os

from dotenv import load_dotenv

from src import logger
from src.databases import DATA_DIR, PostgresDB, ensure_dir


class CsvExport:
    def __init__(self):
        self.db = PostgresDB()
        self.csvpath = os.path.join(DATA_DIR, "data.csv")
        ensure_dir(DATA_DIR)
        self.init_export()

    def init_export(self) -> None:
        try:
            self.export()
        except Exception as e:
            logger.exception(f":: CsvExport: Failed to export data to csv {e}")
        finally:
            self.close()

    def export(self):
        column_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'stockinfo'"
        columns = self.db.fetch(column_query)
        columns = [i[0] for i in columns]

        query = f"SELECT * FROM stockinfo"
        data = self.db.fetch(query)

        with open(self.csvpath, "w") as f:
            csv_writer = csv.writer(f)
            # write headers
            csv_writer.writerow(columns)
            # write data
            csv_writer.writerows(data)
        logger.info(f":: CsvExport: Exported {len(data)} rows.")

    def close(self):
        self.db.close()


if __name__ == "__main__":
    load_dotenv()

    from src import init_logger

    init_logger()

    CsvExport()
    logger.info(f":: CSV File exported to {os.path.abspath(DATA_DIR)}/data.csv")
