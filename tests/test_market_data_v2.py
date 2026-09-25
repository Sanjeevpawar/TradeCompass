from data.providers.mock_provider import MockMarketDataProvider
from analysis.v2.option_features import option_chain_features, select_liquid_candidates


def test_mock_provider_returns_normalized_market_and_chain():
    provider = MockMarketDataProvider()
    market = provider.get_market_snapshot("13", "IDX_I")
    expiries = provider.get_expiries("13", "IDX_I")
    chain = provider.get_option_chain("13", "IDX_I", expiries[0])

    assert market.ltp > 0
    assert chain.underlying_ltp == market.ltp
    assert len(chain.options) > 0


def test_option_features_and_candidates_are_computable():
    provider = MockMarketDataProvider()
    chain = provider.get_option_chain("13", "IDX_I", "2026-09-24")
    features = option_chain_features(chain)

    assert features["valid"] is True
    assert features["pcr"] is not None
    assert features["atm_strike"] is not None
    assert select_liquid_candidates(chain, "CE")
    assert select_liquid_candidates(chain, "PE")
