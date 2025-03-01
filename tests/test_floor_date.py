import pandas as pd
from pandas.testing import assert_series_equal
import pytimetk as tk

def test_floor_date():
    
    dates = pd.DatetimeIndex(['2022-01-04', '2022-01-05', '2022-01-06'])
    
    # Week Flooring
    result = tk.floor_date(dates, 'W')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-03', '2022-01-03', '2022-01-03'])), check_freq=False, check_names=False)
    
    # Month
    result = tk.floor_date(dates, 'M')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-01', '2022-01-01', '2022-01-01'])), check_freq=False, check_names=False)
    
    # Quarter   
    result = tk.floor_date(dates, 'Q')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-01', '2022-01-01', '2022-01-01'])), check_freq=False, check_names=False)
    
    # Year
    result = tk.floor_date(dates, 'Y')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-01', '2022-01-01', '2022-01-01'])), check_freq=False, check_names=False)
    
def test_floor_datetime():
    
    datetimes = pd.DatetimeIndex(['2022-01-04 01:00:01', '2022-01-04 01:00:02', '2022-01-04 01:00:03'])
    
    #  Minute
    result = tk.floor_date(datetimes, 'min')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-04 01:00:00', '2022-01-04 01:00:00', '2022-01-04 01:00:00'])), check_freq=False, check_names=False)
    
    # Hour
    result = tk.floor_date(datetimes, 'H')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-04 01:00:00', '2022-01-04 01:00:00', '2022-01-04 01:00:00'])), check_freq=False, check_names=False)
    
    # Day
    result = tk.floor_date(datetimes, 'D')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-04', '2022-01-04', '2022-01-04'])), check_freq=False, check_names=False)
    
    # Week
    result = tk.floor_date(datetimes, 'W')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-03', '2022-01-03', '2022-01-03'])), check_freq=False, check_names=False)
    
    # Month
    result = tk.floor_date(datetimes, 'M')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-01', '2022-01-01', '2022-01-01'])), check_freq=False, check_names=False)
    
    
def test_ceil_date():
    
    
    dates = pd.DatetimeIndex(['2022-01-04', '2022-01-05', '2022-01-06'])
    
    # Week 
    result = tk.ceil_date(dates, 'W')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-01-10', '2022-01-10', '2022-01-10'])), check_freq=False, check_names=False)
    
    # Month
    result = tk.ceil_date(dates, 'M')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-02-01', '2022-02-01', '2022-02-01'])), check_freq=False, check_names=False)
    
    # Quarter   
    result = tk.ceil_date(dates, 'Q')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2022-04-01', '2022-04-01', '2022-04-01'])), check_freq=False, check_names=False)
    
    # Year
    result = tk.ceil_date(dates, 'Y')
    
    assert_series_equal(result, pd.Series(pd.to_datetime(['2023-01-01', '2023-01-01', '2023-01-01'])), check_freq=False, check_names=False)