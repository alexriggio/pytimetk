import pytimetk as tk
import pandas as pd
import pytest

from itertools import product

threads = [1, 2]
methods = ["twitter", "seasonal_decompose"]
combinations = list(product(threads, methods))

@pytest.mark.parametrize("threads, method", combinations)
def test_01_grouped_anomalize(threads, method):
    
    df = tk.load_dataset("walmart_sales_weekly", parse_dates=["Date"])[["id", "Date", "Weekly_Sales"]]

    anomalize_df = (
        df
            .groupby('id') 
            .anomalize(
                "Date", "Weekly_Sales", 
                period = 52, 
                trend = 52, 
                method = method,
                threads = threads, 
                show_progress = False,
            ) 
    )
    
    expected_colnames = [
        'id',
        'Date',
        'observed',
        'seasonal',
        'seasadj',
        'trend',
        'remainder',
        'anomaly',
        'anomaly_score',
        'anomaly_direction',
        'recomposed_l1',
        'recomposed_l2',
        'observed_clean'
    ]
    
    assert anomalize_df.shape[0] == df.shape[0]
    
    assert expected_colnames == list(anomalize_df.columns)
    
threads = [1]
methods = ["twitter", "seasonal_decompose"]
combinations = list(product(threads, methods))

@pytest.mark.parametrize("threads, method", combinations)
def test_02_ungrouped_anomalize(threads, method):
    
    df = tk.load_dataset("walmart_sales_weekly", parse_dates=["Date"])[["id", "Date", "Weekly_Sales"]].query("id == '1_1'")

    anomalize_df = (
        df
            .groupby('id') 
            .anomalize(
                "Date", "Weekly_Sales", 
                period = 52, 
                trend = 52, 
                method = method,
                threads = threads, 
                show_progress = False,
            ) 
    )
    
    expected_colnames = [
        'id',
        'Date',
        'observed',
        'seasonal',
        'seasadj',
        'trend',
        'remainder',
        'anomaly',
        'anomaly_score',
        'anomaly_direction',
        'recomposed_l1',
        'recomposed_l2',
        'observed_clean'
    ]
    
    assert anomalize_df.shape[0] == df.shape[0]
    
    assert expected_colnames == list(anomalize_df.columns)
    

    