import pandas as pd
import pandas_flavor as pf
import numpy as np

from typing import Union, Optional

from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_value_column
from pytimetk.core.frequency import get_frequency, get_seasonal_frequency, get_trend_frequency

from pytimetk.utils.parallel_helpers import parallel_apply, get_threads, progress_apply

from statsmodels.tsa.seasonal import seasonal_decompose

@pf.register_dataframe_method
def anomalize(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,
    value_column: str,
    period: Optional[int] = None,
    trend: Optional[int] = None,
    method: str = 'twitter',
    decomp: str = 'additive',
    clean: str = 'min_max',
    iqr_alpha: float = 0.05,
    clean_alpha: float = 0.75,
    max_anomalies: float = 0.2,
    bind_data: bool = False,
    threads: int = 1,
    show_progress: bool = True,
    verbose = False,
) -> pd.DataFrame:
    '''
    The `anomalize` function is used to detect anomalies in time series data, 
    either for a single time
    series or for multiple time series grouped by a specific column.
        
    Parameters
    ----------
    data : Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy]
        The input data, which can be either a pandas DataFrame or a pandas 
        DataFrameGroupBy object.
    date_column : str
        The name of the column in the data that contains the dates or timestamps.
    value_column : str
        The name of the column in the data that contains the values to be analyzed 
        for anomalies.
    period : Optional[int]
        The `period` parameter specifies the length of the seasonal component in the 
        time series. It is used in the decomposition process to separate the time 
        series into its seasonal, trend, and remainder components. If not specified, 
        the function will automatically determine the period based on the data.
    trend : Optional[int]
        The `trend` parameter is an optional integer that specifies the length of 
        the moving average window used for trend estimation. If `trend` is set to 
        `None`, no trend estimation will be performed.
    method : str
        The `method` parameter determines the method used for anomaly detection. 
        The available options are 'twitter' and 'seasonal_decompose'. The default 
        value is 'twitter'.
    decomp : str
        The `decomp` parameter specifies the type of decomposition to use for time 
        series decomposition. It can take two values:
        1. 'additive' - This is the default value. It specifies that the time series 
            will be decomposed using an additive model.
        2. 'multiplicative' - This specifies that the time series will be decomposed 
            using a multiplicative model.        
    clean : str
        The `clean` parameter specifies the method used to clean the anomalies. 
        It can take two values:
        
        1. 'min_max' - This specifies that the anomalies will be cleaned using the 
            min-max method. This method replaces the anomalies with the 0.75 * lower 
            or upper bound of the recomposed time series, depending on the direction 
            of the anomaly. The 0.75 multiplier can be adjusted using the 
            `clean_alpha` parameter.
        2. 'linear' - This specifies that the anomalies will be cleaned using 
                    linear interpolation.
    iqr_alpha : float
        The `iqr_alpha` parameter is used to determine the threshold for detecting 
        outliers. It is the significance level used in the interquartile range (IQR) 
        method for outlier detection. 
        - The default value is 0.05, which corresponds to a 5% significance level. 
        - A lower significance level will result in a higher threshold, which means 
        fewer outliers will be detected.
        - A higher significance level will result in a lower threshold, which means 
        more outliers will be detected.
    clean_alpha : float
        The `clean_alpha` parameter is used to determine the threshold for cleaning 
        the outliers. The default is 0.75, which means that the anomalies will be 
        cleaned using the 0.75 * lower or upper bound of the recomposed time series, 
        depending on the direction of the anomaly.
    max_anomalies : float
        The `max_anomalies` parameter is used to specify the maximum percentage of 
        anomalies allowed in the data. It is a float value between 0 and 1. For 
        example, if `max_anomalies` is set to 0.2, it means that the function will 
        identify and remove outliers until the percentage of outliers in the data is 
        less than or equal to 20%. The default value is 0.2.
    bind_data : bool
        The `bind_data` parameter determines whether the original data will be 
        included in the output. If set to `True`, the original data will be included 
        in the output dataframe. If set to `False`, only the anomalous data will be 
        included.
    threads : int
        The `threads` parameter specifies the number of threads to use for parallel 
        processing. By default, it is set to `1`, which means no parallel processing 
        is used. If you set `threads` to `-1`, it will use all available processors 
        for parallel processing.
    show_progress : bool
        A boolean parameter that determines whether to show a progress bar during 
        the execution of the function. If set to True, a progress bar will be 
        displayed. If set to False, no progress bar will be shown.
    verbose: bool
        The `verbose` parameter is a boolean flag that determines whether or not to 
        display additional information and progress updates during the execution of 
        the `anomalize` function. If `verbose` is set to `True`, you will see more 
        detailed output. 
        
    Returns
    -------
    pd.DataFrame
        The `anomalize` function returns a pandas DataFrame containing the original 
        data with additional
    columns:
        - observed: original data
        - seasonal: seasonal component
        - seasadaj: seasonal adjusted
        - trend: trend component
        - remainder: residual component
        - anomaly: Yes/No flag for outlier detection
        - anomaly score: distance from centerline
        - anomaly direction: -1, 0, 1 inidicator for direction of the anomaly
        - recomposed_l1: lower level bound of recomposed time series
        - recomposed_l2: upper level bound of recomposed time series
        - observed_clean: original data with anomalies interpolated
    
    
    Notes
    -----
    ## Performance
    
    This function uses parallel processing to speed up computation for large 
    datasets with many time series groups: 
    
    Parallel processing has overhead and may not be faster on small datasets.
    
    To use parallel processing, set `threads = -1` to use all available processors.
    
    
    Examples
    --------
    ``` {python}
    # EXAMPLE 1: SINGLE TIME SERIES
    import pytimetk as tk
    import pandas as pd
    import numpy as np

    # Create a date range
    date_rng = pd.date_range(start='2021-01-01', end='2024-01-01', freq='MS')

    # Generate some random data with a few outliers
    np.random.seed(42)
    data = np.random.randn(len(date_rng)) * 10 + 25  
    data[3] = 100  # outlier

    # Create a DataFrame
    df = pd.DataFrame(date_rng, columns=['date'])
    df['value'] = data
    
    # Anomalize the data
    anomalize_df = tk.anomalize(
        df, "date", "value",
        method = "twitter", 
        iqr_alpha = 0.10, 
        clean_alpha = 0.75,
        clean = "min_max",
        verbose = True,
    )
    
    anomalize_df.glimpse()
    ```
    
    ``` {python}
    # Visualize the results
    anomalize_df.plot_anomalies_decomp("date")
    ```
    
    ``` {python}
    # Visualize the anomaly bands
    (
         anomalize_df
            .plot_anomalies(
                date_column = "date",
                engine = "plotly",
            )
    )
    ```
    
    ``` {python}
    # Get the anomalies    
    anomalize_df.query("anomaly=='Yes'")
    ```
    
    ``` {python} 
    # Visualize observed vs cleaned
    anomalize_df.plot_anomalies_cleaned("date")
    ```
    
    ``` {python}
    # EXAMPLE 2: MULTIPLE TIME SERIES
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset("walmart_sales_weekly", parse_dates=["Date"])[["id", "Date", "Weekly_Sales"]]
    
    anomalize_df = (
        df
            .groupby('id') 
            .anomalize(
                "Date", "Weekly_Sales", 
                period = 52, 
                trend = 52, 
                threads = 1
            ) 
    )
    
    # Visualize the decomposition results
    
    (
        anomalize_df
            .groupby("id")
            .plot_anomalies_decomp(
                date_column = "Date",
                line_color = "steelblue",
                width = 1200,
                height = 800,
                x_axis_date_labels = "%y",
                engine = 'plotnine',                
            )
    )
    ```
    
    ``` {python}
    # Visualize the anomaly bands
    (
        anomalize_df 
            .groupby(["id"]) 
            .plot_anomalies(
                date_column = "Date", 
                facet_ncol = 2, 
                width = 800,
                height = 800,
                engine = "plotly",
            )
    )
    ```
    
    ``` {python}
    # Get the anomalies    
    anomalize_df.query("anomaly=='Yes'")
    ```
    
    ``` {python}
    # Visualize observed vs cleaned
    (
        anomalize_df
            .groupby(["id"]) 
            .plot_anomalies_cleaned(
                "Date", 
                facet_ncol = 2
            )
    )
    ```
    '''
    
    check_dataframe_or_groupby(data)
    check_date_column(data, date_column)
    check_value_column(data, value_column)
    
    if isinstance(data, pd.DataFrame):
        result = _anomalize(
            data = data, 
            date_column=date_column, 
            value_column=value_column,
            period=period,
            trend=trend,
            method=method,
            decomp=decomp,
            clean=clean,
            iqr_alpha=iqr_alpha,
            clean_alpha=clean_alpha,
            max_anomalies=max_anomalies,
            bind_data=bind_data,
            verbose=verbose,
        )
    
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        
        group_names = data.grouper.names
        
        # Get threads
        threads = get_threads(threads)
        
        if threads == 1:
            
            result = progress_apply(
                data, 
                func = _anomalize, 
                show_progress=show_progress,
                desc="Anomalizing...",
                # kwargs
                date_column=date_column, 
                value_column=value_column,
                period=period,
                trend=trend,
                method=method,
                decomp=decomp,
                clean=clean,
                iqr_alpha=iqr_alpha,
                clean_alpha=clean_alpha,
                max_anomalies=max_anomalies,
                bind_data=bind_data,
                verbose=verbose,
            ).reset_index(level=group_names)
            
        else:
        
            result = parallel_apply(
                data, 
                _anomalize, 
                date_column=date_column, 
                value_column=value_column,
                period=period,
                trend=trend,
                method=method,
                decomp=decomp,
                clean=clean,
                iqr_alpha=iqr_alpha,
                clean_alpha=clean_alpha,
                max_anomalies=max_anomalies,
                bind_data=bind_data,
                threads=threads,
                show_progress=show_progress,
                verbose=verbose,
                desc="Anomalizing...",
            ).reset_index(level=group_names)
    
    return result

# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.anomalize = anomalize


def _anomalize(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,
    value_column: str,
    period: Optional[int] = None,
    trend: Optional[int] = None,
    method: str = 'twitter',
    decomp: str = 'additive',
    clean: str = 'linear',
    iqr_alpha: float = 0.05,
    clean_alpha: float = 0.75,
    max_anomalies: float = 0.2,
    bind_data: bool = False,
    verbose = False,
) -> pd.DataFrame:
    
    orig_date_column = data[date_column]
    
    data = data.copy()
    
    
    
    # STEP 0: Get the seasonal period and trend frequency
    if period is None:
        
        period = get_seasonal_frequency(data[date_column], numeric=True)
        
        period = int(period)
        
        if verbose:
            print(f"Using seasonal frequency of {period} observations")
    
    
    if trend is None:
            
        trend = get_trend_frequency(data[date_column], numeric=True)
        
        trend = int(trend)
        
        if verbose:
            print(f"Using trend frequency of {trend} observations")
    
    # STEP 1: Decompose the time series
    if method == 'twitter':
                    
        median_span = np.round(len(data) / trend)
        median_span = int(median_span)

        result = _twitter_decompose(
            data = data, 
            date_column=date_column, 
            value_column=value_column, 
            period=period,
            median_span=median_span, 
            model=decomp,
        )
    else:
        result = _seasonal_decompose(
            data=data, 
            date_column=date_column, 
            value_column=value_column, 
            period=period,
            model=decomp,
            extrapolate_trend = 'freq'
        )
    
    # STEP 2: Identify the outliers
    
    outlier_df = _iqr(
        data = result, 
        target = 'remainder', 
        alpha = iqr_alpha, 
        max_anoms = max_anomalies
    )
    
    # STEP 3: Recompose the time series
    
    result['anomaly'] = outlier_df['outlier_reported']
    result['anomaly_score'] = outlier_df['score']
    result['anomaly_direction'] = outlier_df['direction']
    
    result['recomposed_l1'] = result['seasonal'] + result['trend'] + outlier_df['remainder_l1']
    
    result['recomposed_l2'] = result['seasonal'] + result['trend'] + outlier_df['remainder_l2']
    
    # STEP 4: Clean the Anomalies
    
    if clean == 'linear':
        result['observed_clean'] = result['observed'] \
            .where(result['anomaly']=='No', np.nan) \
            .interpolate(method=clean, limit_direction='both')
    else:
        # min_max
        result['observed_clean'] = np.where(
            result['anomaly_direction'] == -1, 
            clean_alpha*result['recomposed_l1'],
            np.where(
                result['anomaly_direction'] == 1, 
                clean_alpha*result['recomposed_l2'], 
                result['observed']
            )
        )
        
        
    result[date_column] = orig_date_column
    
    # STEP 5: Bind the data
    if bind_data:
        result = pd.concat([data, result.drop(date_column, axis=1)], axis=1)
    
    return result

 
def _twitter_decompose(
    data, 
    date_column, 
    value_column, 
    period = None, 
    median_span = None,
    model = 'additive',
):
    orig_index = data.index
        
    series = data.set_index(date_column)[value_column]
     
    
    # Need to add freq, trend, and kwargs
    # TODO - Median Seasonal Trend (More robust to outliers)
    result = seasonal_decompose(
        series, 
        period=period,
        model=model,
        extrapolate_trend='freq',
    )
    
    # Construct TS Decomposition DataFrame
    observed = series
    
    seasadj = series - result.seasonal
    seasadj.name = 'seasadj'
    
    # Calculate median trend
    if median_span is None:
        median_span = 4
    
    def repeat_sequence(seq, length_out):
        quotient, remainder = divmod(length_out, len(seq))
        return seq * quotient + seq[:remainder]
    
    df = pd.DataFrame(seasadj)
    
    df['median_index'] = sorted(repeat_sequence(list(range(median_span)), len(seasadj)))
    
    trend = df.groupby('median_index')['seasadj'].transform('median')
    
    resid = seasadj - trend
    
    
    result_df = pd.concat([observed, result.seasonal, seasadj, trend, resid], axis=1)
    
    result_df.columns = ['observed', 'seasonal', 'seasadj', 'trend', 'remainder']
    
    result_df.reset_index(inplace=True)

    
    result_df.index = orig_index
    
    return result_df 
     

def _seasonal_decompose(
    data, 
    date_column, 
    value_column, 
    model='additive',
    period = None, 
    filt=None,
    two_sided=True, 
    extrapolate_trend = 'freq'
):
    
    orig_index = data.index
        
    series = data.set_index(date_column)[value_column]
     
    
    # Need to add freq, trend, and kwargs
    result = seasonal_decompose(
        series, 
        model=model,
        period = period,
        filt=filt,
        two_sided=two_sided,
        extrapolate_trend = extrapolate_trend,
    )
    
    # Construct TS Decomposition DataFrame
    observed = series
    
    seasadj = series - result.seasonal
    
    trend = result.trend
    
    resid = seasadj - trend
        
    result_df = pd.concat([observed, result.seasonal, seasadj, trend, resid], axis=1)
    
    result_df.columns = ['observed', 'seasonal', 'seasadj', 'trend', 'remainder']
    
    result_df.reset_index(inplace=True)
    
    result_df.index = orig_index

    return result_df 

def _iqr(data, target, alpha=0.05, max_anoms=0.2):
    """
    This function is not intended for general use. It is used internally by the anomaly detection functions.
    
    Examples
    --------
    ``` {python}
    import pytimetk as tk
    import pandas as pd
    import numpy as np
    
    # Example Usage:
    df = pd.DataFrame({
        'x': list(range(100)),
        'y': np.random.randn(100)
    })

    outlier_dict = tk.iqr(df, 'y')
    ```
    """
    
    data = data.copy()
    
    # Compute the interquartile range
    q1, q3 = np.percentile(data[target], [25, 75])
    iq_range = q3 - q1
    limits = [-1*(q1 + (0.15 / alpha) * iq_range), q3 + (0.15 / alpha) * iq_range]

    # Identify the outliers
    outlier_idx = (data[target] < limits[0]) | (data[target] > limits[1])
    outlier_vals = data.loc[outlier_idx, target]

    # Calculate the anomaly_score from the centerline
    centerline = sum(limits) / 2
    data['score'] = abs(data[target] - centerline)

    # Yes/No flag for outlier
    data['outlier_reported'] = np.where(data[target] > limits[1], "Yes", np.where(data[target] < limits[0], "Yes", "No"))

    # Direction of the outlier
    data['direction'] = np.where(data[target] > limits[1], 1, np.where(data[target] < limits[0], -1, 0))
    
    # Remainder Limits
    data['remainder_l1'] = limits[0]
    data['remainder_l2'] = limits[1]
    
    return data[['outlier_reported', 'direction', 'score', 'remainder_l1', 'remainder_l2']]
    


