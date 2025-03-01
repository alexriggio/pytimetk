import numpy as np
import pandas as pd
import pandas_flavor as pf
import polars as pl
from typing import Union, List
from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_value_column

from pytimetk.utils.pandas_helpers import flatten_multiindex_column_names
from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_value_column
from pytimetk.utils.polars_helpers import pandas_to_polars_frequency, pandas_to_polars_aggregation_mapping

@pf.register_dataframe_method
def augment_hilbert(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str, 
    value_column: Union[str, List[str]], 
    engine: str = 'pandas'):

    """
    Apply the Hilbert transform to specified columns of a DataFrame or 
    DataFrameGroupBy object.

    Parameters
    ----------
    data : pd.DataFrame or pd.core.groupby.generic.DataFrameGroupBy
        Input DataFrame or DataFrameGroupBy object with one or more columns of 
        real-valued signals.
    value_column : str or list
        List of column names in 'data' to which the Hilbert transform will be 
        applied.
    engine : str, optional
        The `engine` parameter is used to specify the engine to use for 
        summarizing the data. It can be either "pandas" or "polars". 
        
        - The default value is "pandas".
        
        - When "polars", the function will internally use the `polars` library 
        for summarizing the data. This can be faster than using "pandas" for 
        large datasets. 
    
    Returns
    -------
    df_hilbert : pd.DataFrame
        A new DataFrame with the 2 Hilbert-transformed columns added, 1 for the 
        real and 1 for imaginary (original columns are preserved).

    Notes
    -----
    The Hilbert transform is used in time series analysis primarily for:
    
    1. Creating Analytic Signals: Forms a complex-valued signal whose 
    properties (magnitude and phase) provide valuable insights into the 
    original signal's structure.

    2. Determining Instantaneous Phase/Frequency: Offers real-time signal 
    characteristics, crucial for non-stationary signals whose properties 
    change over time.

    3. Extracting Amplitude Envelope: Helps in identifying signal's 
    amplitude variations, useful in various analysis tasks.

    4. Enhancing Signal Analysis: Assists in tasks like demodulation, trend 
    analysis, feature extraction for machine learning, and improving 
    signal-to-noise ratio, providing a deeper understanding of underlying 
    patterns and trends.


    Examples
    --------
    ```{python}
    # Example 1: Using Pandas Engine on a pandas groupby object
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset('walmart_sales_weekly', parse_dates=['Date'])


    df_hilbert = (df
            .groupby('id')
            .augment_hilbert(
                date_column = 'Date',
                value_column = ['Weekly_Sales'],
                engine = 'pandas'
            )
    )

    df_hilbert.head()
    ```
    
    ```{python}
    # Example 2: Using Polars Engine on a pandas groupby object
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset('walmart_sales_weekly', parse_dates=['Date'])
    df_hilbert = (df
            .groupby('id')
            .augment_hilbert(
                date_column = 'Date',
                value_column = ['Weekly_Sales'],
                engine = 'polars'
            )
    )

    df_hilbert.head()
    ```

    # Example 3: Using Polars Engine on a pandas dataframe
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset('taylor_30_min', parse_dates=['date'])
    df_hilbert = (df
            .augment_hilbert(
                date_column = 'date',
                value_column = ['value'],
                engine = 'polars'
            )
    )

    df_hilbert.head()
    ```
    # Example 4: Using Polars Engine on a groupby object
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset('taylor_30_min', parse_dates=['date'])
    df_hilbert_pd = (df
            .augment_hilbert(
                date_column = 'date',
                value_column = ['value'],
                engine = 'pandas'
            )
    )

    df_hilbert.head()
    ```
    """
    # Run common checks
    check_dataframe_or_groupby(data)
    check_value_column(data, value_column)
    check_date_column(data, date_column)
        
    if engine == 'pandas':
        return _augment_hilbert_pandas(data, date_column, value_column)
    elif engine == 'polars':
        return _augment_hilbert_polars(data, date_column, value_column)
    else:
        raise ValueError("Invalid engine. Use 'pandas' or 'polars'.")
# Monkey-patch the method to the DataFrameGroupBy class
pd.core.groupby.DataFrameGroupBy.augment_hilbert = augment_hilbert


def _augment_hilbert_pandas(                            
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str,
    value_column: Union[str, List[str]], 
                            ):
    # Type checks
    # if not isinstance(data, (pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy)):
    #     raise TypeError("Input must be a pandas DataFrame or DataFrameGroupBy object")
    if not isinstance(value_column, list) or not all(isinstance(col, str) for col in value_column):
        raise TypeError("value_column must be a list of strings")

    # If 'data' is a DataFrame, convert it to a groupby object with a dummy group
    if isinstance(data, pd.DataFrame):
        if any(col not in data.columns for col in value_column):
            missing_cols = [col for col in value_column if col not in data.columns]
            raise KeyError(f"Columns {missing_cols} do not exist in the DataFrame")
        #data = data.groupby(np.zeros(len(data))).sort(by=date_column)
        data = data.sort_values(by=date_column)
        data = data.groupby(np.zeros(len(data)))

    
    # Function to apply Hilbert transform to each group
    def apply_hilbert(group):
        for col in value_column:
            # Ensure the column exists in the DataFrame
            if col not in group.columns:
                raise KeyError(f"Column '{col}' does not exist in the group")

            # Get the signal from the DataFrame
            signal = group[col].values

            # Compute the FFT of the signal
            N = signal.size
            Xf = np.fft.fft(signal)
            
            # Create a zero-phase version of the signal with the negative 
            # frequencies zeroed out
            h = np.zeros(N)
            if N % 2 == 0:
                h[0] = h[N // 2] = 1
                h[1:N // 2] = 2
            else:
                h[0] = 1
                h[1:(N + 1) // 2] = 2

            Xf *= h
            
            # Perform the inverse FFT
            x_analytic = np.fft.ifft(Xf)
            
            # Update the DataFrame
            group[f'{col}_hilbert_real'] = np.real(x_analytic)
            group[f'{col}_hilbert_imag'] = np.imag(x_analytic)
        return group

    # Apply the Hilbert transform to each group and concatenate the results
    df_hilbert = pd.concat((apply_hilbert(group) for _, group in data), ignore_index=True)

    return df_hilbert


def _augment_hilbert_polars(    
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str,
    value_column: Union[str, List[str]], 
):
    

        # Function to apply Hilbert transform
    def apply_hilbert(pl_df):
        
        for col in value_column:
            # Compute the Hilbert transform
            signal = pl_df[col].to_numpy()
            N = signal.size
            Xf = np.fft.fft(signal)
            
            # Create a zero-phase version of the signal with the negative frequencies zeroed out
            h = np.zeros(N)
            if N % 2 == 0:
                h[0] = h[N // 2] = 1
                h[1:N // 2] = 2
            else:
                h[0] = 1
                h[1:(N + 1) // 2] = 2

            Xf *= h

            # Perform the inverse FFT
            x_analytic = np.fft.ifft(Xf)
            
            # Convert numpy arrays to Polars Series and add the Hilbert columns to the Polars DataFrame
            real_series = pl.Series(f'{col}_hilbert_real', np.real(x_analytic))
            imag_series = pl.Series(f'{col}_hilbert_imag', np.imag(x_analytic))

            pl_df = pl_df.with_columns(real_series).with_columns(imag_series)
        return pl_df

    # Check if the input data is a DataFrame or a GroupBy object
    grouped = False
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        grouped = True
        # Extract names from groupby object
        groups = data.grouper.names  # This can be a list of group names

        # Convert the GroupBy object into a Polars DataFrame
        df_pl = (
            pl.from_pandas(data.apply(lambda x: x))
                 .groupby(groups, maintain_order=True)
                 .agg(pl.all().sort_by(date_column))
        )

        # Create a list of column names to explode
        columns_to_explode = [col for col in df_pl.columns if col not in groups]

        # Explode the selected columns
        exploded_df = df_pl.explode(columns=columns_to_explode)
        
        #df_temp = pl.DataFrame(data)
        # Group by groups and date
        data = (
            exploded_df
                #.select(groups + [date_column] + value_column)
                #.select(pl.all() )
                #.with_columns(pl.col(date_column))
                .sort(*groups ,date_column)
                #.groupby(groups + [date_column], maintain_order=True)
                #.agg(pl.all().flatten())
                #.sort(groups + [date_column])
                #.explode(columns_to_explode)
        )
        grouped = data.groupby(groups)
        result_pl_df = grouped.apply(apply_hilbert)
        
    else:
        data = (
            pl.from_pandas(data)
                 .sort(date_column)
        )
        result_pl_df = apply_hilbert(data)


    # Convert the Polars DataFrame back to a Pandas DataFrame
    result_pd_df = result_pl_df.to_pandas()                               

    return result_pd_df


