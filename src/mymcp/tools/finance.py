import os
import pandas as pd
from tabulate import tabulate

from fredapi import Fred
from mymcp.tools.fred_series import FRED_series
from pandas import Series
from mymcp.utils import query_document

class FRED:
    def __init__(self):
        """
        Initializes the FRED class with the given API key.
        
        Args:
            API_KEY (str):
                The API key to authenticate with the FRED API.
                
        Attributes:
            fred (Fred):
                An instance of the Fred class from the fredapi package, 
                used to make API calls to FRED.
        """       
        assert os.environ['FRED_API_KEY'], f"Missing FRED_API_KEY"
                
        self.fred = Fred(api_key=os.environ['FRED_API_KEY'])
        
    def get_indicators_list(self) -> str:
        """
        Gets list of available economic indicator tickers
        
        Args:
            question (str):
                The question to use for retrieving FRED series. Be specific about the thing you want to search for.
                
        Returns:
            str:
                A string representation of the search results.
                - If the search is successful, returns the details of the top matching series.
                - If the search fails, it may return an empty string or an error message.
        """
        
        return FRED_series[:250]

                
    def get_indicator_values(self, id: str, years: int = 1) -> Series:
        """
        Retrieves values for the specified economic indicator ticker, filters it for the last 24 months,
        resamples the data to monthly frequency (using the end of the month)
        
        Args:
            id (str):
                The ticker identifier of the FRED series to retrieve.
                
        Returns:
            str:
                A string representation of the filtered and resampled series data.
                - If the retrieval and processing are successful, returns the series data as a string.
                - If an error occurs during the query or processing, returns an error message indicating the failure.
        """
        try:
            series:Series = self.fred.get_series(id)
            end_date = series.index.max()
            start_date = end_date - pd.DateOffset(months=years*12)
            subset = series[start_date:end_date]
            subset = subset.resample('ME').last()        
            return subset
        except Exception as e:
            return f"Error querying '{id}': {str(e)}"
