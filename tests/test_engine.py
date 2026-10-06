import pytest
from pims.engine.quant import QuantEngine
from pims.engine.llm import MockAdapter, ModelResponse

def test_quant_per():
    assert QuantEngine.calculate_per(150.0, 10.0) == 15.0
    assert QuantEngine.calculate_per(150.0, 0.0) is None
    assert QuantEngine.calculate_per(150.0, -5.0) is None

def test_quant_pbr():
    assert QuantEngine.calculate_pbr(50.0, 25.0) == 2.0
    assert QuantEngine.calculate_pbr(50.0, 0.0) is None

def test_quant_roe():
    assert QuantEngine.calculate_roe(100.0, 1000.0) == 10.0
    assert QuantEngine.calculate_roe(-50.0, 1000.0) == -5.0
    assert QuantEngine.calculate_roe(100.0, 0.0) is None

def test_quant_roic():
    assert QuantEngine.calculate_roic(150.0, 1500.0) == 10.0
    assert QuantEngine.calculate_roic(150.0, 0) is None

def test_quant_fcf():
    assert QuantEngine.calculate_fcf(500.0, 150.0) == 350.0
    assert QuantEngine.calculate_fcf(500.0, -150.0) == 350.0 # Tests absolute value logic

def test_quant_portfolio_weights():
    positions = {"AAPL": 1000.0, "MSFT": 2000.0}
    cash = 1000.0

    weights = QuantEngine.calculate_portfolio_weights(positions, cash)

    assert weights["AAPL"] == 0.25
    assert weights["MSFT"] == 0.50
    assert weights["CASH"] == 0.25

    # Test empty portfolio
    weights_empty = QuantEngine.calculate_portfolio_weights({}, 0)
    assert weights_empty == {}

def test_quant_drawdown():
    assert QuantEngine.calculate_drawdown(1000.0, 900.0) == 10.0
    assert QuantEngine.calculate_drawdown(1000.0, 1000.0) == 0.0
    assert QuantEngine.calculate_drawdown(1000.0, 1100.0) == 0.0 # Price is higher than peak
    assert QuantEngine.calculate_drawdown(0.0, 100.0) == 0.0

def test_mock_llm_adapter():
    adapter = MockAdapter()
    response = adapter.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Analyze AAPL"
    )

    assert isinstance(response, ModelResponse)
    assert response.model == "mock-model-fast"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.estimated_cost > 0.0
    assert response.latency_ms > 0
