from pathlib import Path

from scripts.validate_historical_backtest_integration import validate


def test_integration_rejects_missing_underlying(tmp_path: Path):
    try:
        validate(tmp_path / 'missing_underlying.csv', tmp_path / 'missing_options.csv')
    except FileNotFoundError as exc:
        assert 'Underlying dataset not found' in str(exc)
    else:
        raise AssertionError('Expected missing underlying failure')


def test_integration_uses_full_year_paths():
    from scripts.validate_historical_backtest_integration import DEFAULT_UNDERLYING, DEFAULT_OPTIONS
    assert str(DEFAULT_UNDERLYING).endswith('data/dhan_history/reconstructed/nifty_underlying_1y.csv')
    assert str(DEFAULT_OPTIONS).endswith('data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv')
