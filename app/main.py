import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.gotify_client import GotifyClient

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, get_aggregated_resources
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import google.auth
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from google.auth.transport.requests import Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
#from opentelemetry.resourcedetector.gcp import GCEResourceDetector, GKEResourceDetector, CloudRunResourceDetector

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Environment Variables
GOTIFY_ENDPOINT = os.getenv("GOTIFY_ENDPOINT", "https://gotify.tpk.pw")
GOTIFY_USERNAME = os.getenv("GOTIFY_USERNAME", "")
GOTIFY_PASSWORD = os.getenv("GOTIFY_PASSWORD", "")
NOTIFYPASS = os.getenv("NOTIFYPASS")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

# OpenTelemetry Setup
def setup_otel(app: FastAPI):
    attributes = {
        "service.name": "gotifyme",
        "service.namespace": "gotifyme-ns",
    }
    if GOOGLE_CLOUD_PROJECT:
        attributes["gcp.project_id"] = GOOGLE_CLOUD_PROJECT
        
    resource = Resource.create(attributes)
    
    # Aggregate resources from GCP detectors
    #resource = get_aggregated_resources(
    #    [
    #        GKEResourceDetector(),
    #        GCEResourceDetector(),
    #        CloudRunResourceDetector(),
    #    ],
    #    initial_resource=resource,
    #)

    # Configure OTLP Exporter for Google Cloud Trace
    # Using telemetry.googleapis.com:443 for gRPC as per best practices
    headers = []
    if GOOGLE_CLOUD_PROJECT:
        headers.append(("x-goog-user-project", GOOGLE_CLOUD_PROJECT))
    
    # Manually create credentials with the required scope
    scopes = ["https://www.googleapis.com/auth/trace.append"]
    credentials, _ = google.auth.default(scopes=scopes)
    grpc_credentials = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(AuthMetadataPlugin(credentials, Request()))
    )

    otlp_exporter = OTLPSpanExporter(
        endpoint="telemetry.googleapis.com:443",
        credentials=grpc_credentials,
        headers=tuple(headers) if headers else None,
    )

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument Requests (outgoing calls to Gotify)
    RequestsInstrumentor().instrument()
    
    # Instrument Logging (inject trace IDs into logs)
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

# Setup OTEL
if os.getenv("ENABLE_OTEL", "false").lower() == "true":
    setup_otel(app)

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
