"""
isort:skip_file
"""
from src.scrapers.stock_analysis_api import StockAnalysisAPI
from src.scrapers.yahooapi import YahooAPI

ScraperType = YahooAPI | StockAnalysisAPI

# main imports this file so at last also
from src.scrapers.main import scraper_instance
