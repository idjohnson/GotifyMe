import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.gotify_client import GotifyClient

# OpenTelemetry Imports
from opentelemetry import trace, metrics, _logs
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
GOTIFY_ENDPOINT = os.getenv("GOTIFY_ENDPOINT", "https://gotify.tpk.pw")
GOTIFY_USERNAME = os.getenv("GOTIFY_USERNAME", "")
GOTIFY_PASSWORD = os.getenv("GOTIFY_PASSWORD", "")
NOTIFYPASS = os.getenv("NOTIFYPASS")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://192.168.1.143:9999")

# OpenTelemetry Setup
resource = Resource.create({"service.name": "notify-app"})

# Tracing
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)))
trace.set_tracer_provider(tracer_provider)

# Metrics
metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True))
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Logs
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)))
_logs.set_logger_provider(logger_provider)

# Integrate OTEL with standard logging
otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(otel_handler)
LoggingInstrumentor().instrument(set_logging_format=True)

client = GotifyClient(GOTIFY_ENDPOINT, GOTIFY_USERNAME, GOTIFY_PASSWORD)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up... Setting up Gotify Client")
    try:
        client.setup_token()
        # Send Hello World on startup as per "The first goal"
        client.send_notification("System", "Hello World - NotifyApp Started")
        logger.info("Startup notification sent.")
    except Exception as e:
        logger.error(f"Failed to initialize Gotify client: {e}")
        # We don't crash the app, but notify endpoints will fail
    
    yield
    
    # Shutdown logic (optional)
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Instrument FastAPI and Requests
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class NotificationRequest(BaseModel):
    title: str
    message: str
    priority: int = 5
    password: str | None = None

@app.get("/")
async def read_index():
    return FileResponse('app/static/index.html')

@app.post("/notify")
async def send_notification(notification: NotificationRequest):
    if NOTIFYPASS:
        if notification.password != NOTIFYPASS:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid password")

    if not client.app_token:
        # Try to setup again if it failed on startup
        try:
            client.setup_token()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gotify configuration error: {str(e)}")

    try:
        result = client.send_notification(notification.title, notification.message, notification.priority)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
