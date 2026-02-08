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
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import google.auth
from google.auth.transport.requests import Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

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
    # Log relevant environment variables for debugging
    for env_var in ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "ENABLE_OTEL", "GOTIFY_ENDPOINT"]:
        logger.debug(f"Env: {env_var}={os.getenv(env_var)}")
        
    # Manually create credentials with the required scope
    # 'cloud-platform' ensures we have all necessary permissions for GCP services
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials, detected_project_id = google.auth.default(scopes=scopes)
    
    # Use detected project ID if not explicitly provided in environment
    project_id = GOOGLE_CLOUD_PROJECT or detected_project_id
    
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.debug(f"GCP Auth: GOOGLE_APPLICATION_CREDENTIALS is set to: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    else:
        logger.debug("GCP Auth: GOOGLE_APPLICATION_CREDENTIALS is NOT set, using default credentials.")

    logger.debug(f"GCP Auth: Project ID being used: {project_id} (Detected: {detected_project_id}, Env: {GOOGLE_CLOUD_PROJECT})")

    if hasattr(credentials, "service_account_email"):
        logger.debug(f"GCP Auth: Service Account Email: {credentials.service_account_email}")
    else:
        logger.debug(f"GCP Auth: Credentials type: {type(credentials)}")

    # Refresh credentials to ensure we have a valid token
    credentials.refresh(Request())
    logger.debug(f"GCP Auth: Credentials valid: {credentials.valid}")
    logger.debug(f"GCP Auth: Credentials expired: {credentials.expired}")
    if hasattr(credentials, "scopes"):
        logger.debug(f"GCP Auth: Scopes: {credentials.scopes}")

    attributes = {
        "service.name": "gotifyme",
        "service.namespace": "gotifyme-ns",
    }
    if project_id:
        attributes["gcp.project_id"] = project_id
        
    resource = Resource.create(attributes)
    logger.debug(f"OTEL Resource Attributes: {resource.attributes}")
    
    # Aggregate resources from GCP detectors
    #resource = get_aggregated_resources(
    #    [
    #        GKEResourceDetector(),
    #        GCEResourceDetector(),
    #        CloudRunResourceDetector(),
    #    ],
    #    initial_resource=resource,
    #)

    # Configure Google Cloud Trace Exporter
    # This uses the native Google Cloud client and automatically handles credentials
    
    try:
        #trace_exporter = GoogleCloudTraceExporter(project_id=project_id)
        trace_exporter = CloudTraceSpanExporter(project_id=project_id)
                                                  
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        span_processor = BatchSpanProcessor(trace_exporter)
        tracer_provider.add_span_processor(span_processor)
        logger.info(f"OpenTelemetry configured successfully for Google Cloud Trace (Project: {project_id})")
    except Exception as e:
        logger.warning(f"Failed to configure OpenTelemetry exporter: {e}. App will continue without trace export. "
                      f"To fix: 1) Ensure Cloud Trace API is enabled in GCP Console, "
                      f"2) Verify service account has 'roles/cloudtrace.agent' role.")

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
