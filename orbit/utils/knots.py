import numpy as np
import pandas as pd
from ..exceptions import IllegalArgument


def get_knot_dates(start_date, knot_idx, freq):
    knot_dates = knot_idx * np.timedelta64(1, freq) + start_date
    return knot_dates


def get_dates_delta(start_date, end_date, freq):
    """Returns knot index based on date difference normalized with the number of steps by frequency provided

    Parameters
    ----
    start_date : numpy datetime
    end_date : numpy datetime array
    freq : pd.infer_freq
    """
    date_diff = end_date - start_date
    # can also be deemed as the "knot_idx"
    norm_delta = np.array(date_diff / np.timedelta64(1, freq)).astype(int)
    return norm_delta


def get_knot_idx_by_dist(num_of_obs, knot_distance):
    """function to calculate the knot idx based on num_of_obs and knot_distance."""
    # starts with the the ending point
    # use negative values or simply append 0 to the sequence?
    knot_idx = np.sort(np.arange(num_of_obs - 1, -1, -knot_distance))
    if 0 not in knot_idx:
        # knot_idx = np.sort(np.arange(num_of_obs - 1, -1 - knot_distance, -knot_distance))
        knot_idx = np.sort(np.append(knot_idx, 0))

    return knot_idx


def get_knot_idx(
        date_array=None,
        num_of_obs=None,
        knot_dates=None,
        knot_distance=None,
        num_of_segments=None,
        date_freq=None):
    """ function to get the knot locations. This function will be used in KTRLite and KTRX model.

    Parameters
    ----------
    num_of_obs : int
        number of observations to derive segments and knots; will be ignored if knot_dates is not None
    date_array : datetime array
        only used when knot_dates is not None
    knot_dates : list or numpy datetime array
        list of dates in string format (%Y-%m-%d) or numpy datetime array which will be used as the knot locations
    knot_distance : int
        distance between every two knots
    num_of_segments : int
        number of segments, which will be used to calculate the knot distance
    date_freq : str
        the date frequency of the input data; only used when knot_dates is not None

    Returns
    -------
    an array of integers, which are the knot location indices (starts at 0).

    """
    if knot_dates is None and num_of_obs is None:
        raise IllegalArgument('Either date_array or num_of_obs need to be provided.')

    if knot_dates is not None:
        if date_array is None:
            raise IllegalArgument('When knot_dates are supplied, users need to supply date_array as well.')
        knot_dates = np.array(knot_dates, dtype='datetime64')

        # filter out
        _knot_dates = pd.to_datetime([
            x for x in knot_dates if
            (x <= date_array.max()) and (x >= date_array.min())
        ])

        if date_freq is None:
            # infer date freq if not supplied
            date_freq = pd.infer_freq(date_array)[0]

        knot_idx = get_dates_delta(
            start_date=date_array[0],
            end_date=_knot_dates,
            freq=date_freq
        )

    elif knot_distance is not None:
        if not isinstance(knot_distance, int):
            raise Exception("knot_distance must be an int.")
        knot_idx = get_knot_idx_by_dist(num_of_obs, knot_distance)

    elif num_of_segments is not None:
        knot_distance = np.round((num_of_obs - 1) / num_of_segments).astype(int)
        knot_idx = get_knot_idx_by_dist(num_of_obs, knot_distance)
    else:
        raise Exception("please specify at least one of the followings to determine the knot locations: "
                        "knot_dates, knot_distance, or num_of_segments.")

    # knot_idx starts with 0; need to add 1 when calculate the fraction
    return knot_idx