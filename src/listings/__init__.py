from src.listings.slick_charts import SandP500, Nasdaq100, DowJones30
from src.listings.nyse import NYSE

listings_map = {
    "dowjones30": DowJones30,
    "nasdaq100": Nasdaq100,
    "sandp500": SandP500,
    "nyse": NYSE,
}
