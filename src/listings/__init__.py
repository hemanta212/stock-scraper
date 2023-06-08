from src.listings.nyse import NYSE
from src.listings.slick_charts import DowJones30, Nasdaq100, SandP500

listings_map = {
    "dowjones30": DowJones30,
    "nasdaq100": Nasdaq100,
    "sandp500": SandP500,
    "nyse": NYSE,
}
