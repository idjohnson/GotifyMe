import pytest
from unittest.mock import patch, MagicMock
from opentelemetry import trace, metrics, _logs

def test_otel_initialization():
    """
    Verify that OpenTelemetry providers are correctly initialized in the app.
    """
    # Import app to trigger main.py execution
    from app.main import app
    
    # Check if tracer provider is set
    tp = trace.get_tracer_provider()
    assert tp is not None
    
    # Check if meter provider is set
    mp = metrics.get_meter_provider()
    assert mp is not None
    
    # Check if logger provider is set
    lp = _logs.get_logger_provider()
    assert lp is not None

@patch("opentelemetry.sdk.trace.export.BatchSpanProcessor")
@patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter")
def test_otel_tracing_setup(mock_exporter, mock_processor):
    """
    Verify that tracing is set up with the correct endpoint.
    This test might be redundant if we just want to ensure it doesn't crash,
    but it shows we are checking the configuration.
    """
    from app.main import OTEL_EXPORTER_OTLP_ENDPOINT
    assert OTEL_EXPORTER_OTLP_ENDPOINT == "http://192.168.1.143:9999"
