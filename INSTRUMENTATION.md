# OpenTelemetry Instrumentation with Google Cloud Observability

This project is instrumented with OpenTelemetry (OTEL) to provide distributed tracing, metrics, and logs, exported to Google Cloud Observability.

## Features

- **Tracing**: Exported to Google Cloud Trace.
- **Metrics**: Exported to Google Cloud Monitoring. Includes a custom counter `notifications_sent_total`.
- **Logs**: Integrated with Google Cloud Logging. Trace and Span IDs are automatically injected and correlated in the Cloud Logging console.

## Prerequisites

1.  **Service Account Permissions**: The SA we use should have at least: "Cloud Telemetry Writer", "Cloud Trace Agent", "Logs Writer" and "Monitoring Metric Writer" permissions.  I have personally also added "Cloud Telemetry Metrics Writer" and "Monitoring Metrics Scopes Viewer (beta)", but I don't think they are required.
1.  **Google Cloud Project**: You must have a Google Cloud project with the Cloud Trace API enabled.
2.  **Authentication (ADC)**: The application uses Application Default Credentials (ADC).
    - For local development, run:
      ```bash
      gcloud auth application-default login
      ```
    - **Local Docker/Container Authentication**: To use ADC inside a local container, mount your local gcloud config and set the environment variable:
      ```bash
      docker run -e ENABLE_OTEL=true \
        -e GOOGLE_CLOUD_PROJECT=your-project-id \
        -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/application_default_credentials.json \
        -v ~/.config/gcloud:/tmp/keys \
        your-image-name
      ```
3.  **Environment Variables**:
    - `ENABLE_OTEL`: Set to `true` to enable instrumentation.
    - `GOOGLE_CLOUD_PROJECT`: Set to your Google Cloud Project ID. This is used for the `x-goog-user-project` header required by the Google Cloud OTLP endpoint.

## Installation

The required packages are listed in `requirements.txt`:

```text
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-requests
opentelemetry-resourcedetector-gcp
opentelemetry-instrumentation-logging
opentelemetry-exporter-credential-provider-gcp
```

Install them using:
```bash
pip install -r requirements.txt
```

## Configuration in Code

The instrumentation is initialized in `app/main.py` via the `setup_otel(app)` function.

- **FastAPI**: Automatically instruments incoming HTTP requests for traces.
- **Requests**: Automatically instruments outgoing calls to the Gotify server.
- **Metrics**: Uses `opentelemetry-exporter-gcp-monitoring` to send metrics to Cloud Monitoring every 60 seconds.
- **Logging**: Uses `google-cloud-logging` to send application logs to Cloud Logging, with OTel context injection for log-trace correlation.
- **Resource Detection**: Uses `opentelemetry-resourcedetector-gcp` to automatically detect metadata.

## Exporting Telemetry

Telemetry is sent to the Google Cloud OTLP endpoint:
`telemetry.googleapis.com:443`

This endpoint uses gRPC via the `OTLPSpanExporter`.

## References

- [Migrate to OTLP Endpoints (Python)](https://docs.cloud.google.com/stackdriver/docs/instrumentation/migrate-to-otlp-endpoints#telemetry_auth_headers-python)
- [Set up ADC for Local Development](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
