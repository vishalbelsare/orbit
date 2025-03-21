import pytest
import pandas as pd
import numpy as np

from orbit.diagnostics.backtest import TimeSeriesSplitter, BackTester
from orbit.diagnostics.metrics import smape, wmape, mape, mse, mae, rmsse
from orbit.models.lgt import LGTMAP
from orbit.models.ktrlite import KTRLiteMAP

@pytest.mark.parametrize(
    "scheduler_args",
    [
        {
            'min_train_len': 100,
            'incremental_len': 100,
            'forecast_len': 20
        },
        {
            'incremental_len': 100,
            'forecast_len': 20,
            'n_splits': 3
        },
        {
            'forecast_len': 20,
            'n_splits': 1
        },
        {
            'forecast_len': 1,
            'n_splits': 3
        }
    ],
    ids=['use_min_train_len', 'use_n_splits', 'single_split', 'one_forecast_len']
)
def test_time_series_splitter(scheduler_args):
    np_array = np.random.randn(300, 4)
    df = pd.DataFrame(np_array)

    tss = TimeSeriesSplitter(
        df=df,
        **scheduler_args,
    )

    assert tss.n_splits == len(list(tss.split()))


@pytest.mark.parametrize(
    "scheduler_args",
    [
        {
            'min_train_len': 100,
            'incremental_len': 100,
            'forecast_len': 20
        },
        {
            'incremental_len': 100,
            'forecast_len': 20,
            'n_splits': 3
        },
        {
            'forecast_len': 20,
            'n_splits': 1
        },
        {
            'forecast_len': 1,
            'n_splits': 3
        }
    ],
    ids=['use_min_train_len', 'use_n_splits', 'single_split', 'one_forecast_len']
)
def test_backtester_sceduler_args(iclaims_training_data, scheduler_args):
    df = iclaims_training_data

    lgt = LGTMAP(
        response_col='claims',
        date_col='week',
        seasonality=1,
        verbose=False
    )

    backtester = BackTester(
        model=lgt,
        df=df,
        **scheduler_args,
    )

    backtester.fit_predict()
    eval_out = backtester.score(metrics=[smape])
    assert np.all(eval_out['metric_values'].values > 0)


@pytest.mark.parametrize(
    "metrics",
    [None, [smape, wmape, mae], smape],
    ids=['default', 'multi-metrics', 'single-metric']
)
def test_backtester_test_metrics(iclaims_training_data, metrics):
    df = iclaims_training_data

    lgt = LGTMAP(
        response_col='claims',
        date_col='week',
        seasonality=1,
        verbose=False
    )

    backtester = BackTester(
        model=lgt,
        df=df,
        forecast_len=3,
        n_splits=1,
    )

    backtester.fit_predict()
    eval_out = backtester.score(metrics=metrics)
    evaluated_metrics = set(eval_out['metric_name'].tolist())

    if metrics is None:
        expected_metrics = [x.__name__ for x in backtester._default_metrics]
    elif isinstance(metrics, list):
        expected_metrics = [x.__name__ for x in metrics]
    else:
        expected_metrics = [metrics.__name__]

    assert set(expected_metrics) == evaluated_metrics

@pytest.mark.parametrize(
    "missing_flag",
    [False, True],
    ids=['full-values', 'missing-values']
)
def test_backtester_ktr_and_missing_val(make_daily_data, missing_flag):
    train_df, test_df, _ = make_daily_data
    df = pd.concat([train_df, test_df], axis=0, ignore_index=True)
    if missing_flag:
        # create a missing value in testing
        df.loc[df.shape[0] - 3, 'response'] = np.nan
        # create a missing value in training
        df.loc[10, 'response'] = np.nan

    ktr = KTRLiteMAP(
        date_col='date',
        response_col='response',
        seasonality=[365.25],
        verbose=False
    )

    bt = BackTester(
        model=ktr,
        df=df,
        n_splits=3,
        incremental_len=100,
        forecast_len=20,
    )

    bt.fit_predict()
    predicted_df = bt.get_predicted_df()
    assert set(predicted_df['split_key'].tolist()) == {0, 1, 2}

    bt_score_df = bt.score(include_training_metrics=False)
    num_testing_metrics = 6
    expected_shape = (num_testing_metrics, 3)
    assert bt_score_df.shape == expected_shape

    testing_metrics_df = bt_score_df[~bt_score_df['is_training_metric']]
    # rmsse is the only one not working for null values; otherwise, they should have valid values
    if missing_flag:
        metric_vals = testing_metrics_df.loc[
            testing_metrics_df['metric_name'] != 'rmsse', 'metric_values'].values
        assert np.all(~np.isnan(metric_vals))
        missing_metric_val = testing_metrics_df.loc[
            testing_metrics_df['metric_name'] == 'rmsse', 'metric_values'].values
        assert np.all(np.isnan(missing_metric_val))
    else:
        metric_vals = testing_metrics_df['metric_values'].values
        assert np.all(~np.isnan(metric_vals))


def test_backtester_with_training_data(iclaims_training_data):
    df = iclaims_training_data

    lgt = LGTMAP(
        response_col='claims',
        date_col='week',
        seasonality=1,
        verbose=False
    )

    backtester = BackTester(
        model=lgt,
        df=df,
        min_train_len=100,
        incremental_len=100,
        forecast_len=20,
    )

    backtester.fit_predict()
    eval_out = backtester.score(include_training_metrics=True)
    evaluated_test_metrics = set(eval_out.loc[~eval_out['is_training_metric'], 'metric_name'].tolist())
    evaluated_train_metrics = set(eval_out.loc[eval_out['is_training_metric'], 'metric_name'].tolist())

    expected_test_metrics = [x.__name__ for x in backtester._default_metrics]

    expected_train_metrics = list(filter(
        lambda x: backtester._get_metric_callable_signature(x) == {'actual', 'predicted'}, backtester._default_metrics)
    )
    expected_train_metrics = [x.__name__ for x in expected_train_metrics]

    assert set(expected_test_metrics) == evaluated_test_metrics
    assert set(expected_train_metrics) == evaluated_train_metrics

    # default metric has 6 values where rmsse is only used in test metric
    num_training_metrics = 5
    num_testing_metrics = 6

    train_metric_val = eval_out.loc[eval_out['is_training_metric'], 'metric_values'].values
    test_metric_val = eval_out.loc[~eval_out['is_training_metric'], 'metric_values'].values

    assert len(train_metric_val) == num_training_metrics
    assert len(test_metric_val) == num_testing_metrics
    assert np.all(~np.isnan(train_metric_val))
    assert np.all(~np.isnan(test_metric_val))
