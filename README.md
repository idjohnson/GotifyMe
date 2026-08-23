![gotifylogo-sm.png](gotifylogo-sm.png)

# GotifyMe

GotifyMe is a notification application that uses [Gotify](https://github.com/gotify/server). The application runs as a containerized Python [FastAPI](https://fastapi.tiangolo.com/) service. It provides a web interface to send notifications to a Gotify server. The application uses a password for basic authorization.

## Overview

This application operates as an intermediary service for a private Gotify server. It lets external applications send push notifications through a single application key. This configuration removes the requirement to manage multiple application keys across different systems.

## Key Features

- **Authentication**: The application first tries to authenticate to the Gotify server with the password as a client token. If this step fails, the application uses basic authentication with the username and password.
- **Token Management**: The application finds or creates a Gotify application named `FastAPI_Notify_App` to get an application token.
- **Web Interface**: A web form at `/` lets users send custom notifications.
- **Startup Test**: The application sends a test notification when it starts to check the connection.
- **API Documentation**: Interactive OpenAPI documentation is available at `/docs` (Swagger) and `/redoc` (ReDoc).

## Key Files

- `app/main.py`: Entry point for the FastAPI application.
- `app/gotify_client.py`: Code for Gotify API authentication and messaging.
- `app/static/index.html`: User interface for the web form.
- `Dockerfile`: Container specification that listens on port 80.
- `requirements.txt`: List of Python dependencies.

## Key Directories

- `tests/`: Contains test scripts for `pytest`.
- `charts/`: Contains Helm charts for Kubernetes deployment.

## Usage

### Execute with Docker

1. Build the Docker image:

   ```bash
   docker build -t notify-app .
   ```

2. Start the Docker container:

   ```bash
   docker run -p 8080:80 \
       -e GOTIFY_ENDPOINT="https://gotify.tpk.pw" \
       -e GOTIFY_USERNAME="myappname" \
       -e GOTIFY_PASSWORD="xxxx.xxxxxx" \
       -e NOTIFYPASS="mypassword" \
       notify-app
   ```

3. Open `http://localhost:8080` in your web browser.

### Execute Locally in Development Mode

1. Create a Python virtual environment:

   ```bash
   python3 -m venv venv
   ```

2. Activate the virtual environment:

   ```bash
   source venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the Uvicorn server:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. Open `http://localhost:8000` in your web browser.

## Deployment on Kubernetes

The default configuration values are located in `charts/gotifyme/values.yaml`.

NOTE: A public container image is available at `harbor.freshbrewed.science/library/notifyapp:0.2`. You can change the repository and tag in your configuration file.

### Install with Default Values

Run this command to install the Helm chart:

```bash
helm install gotifyme ./charts/gotifyme
```

### Install with a Custom Values File

Run this command to install the Helm chart in a custom namespace:

```bash
helm install gotifyme -f ./myvalues.yaml -n mynamespace ./charts/gotifyme
```

## Mobile Applications

- **Android**: Download the Gotify client from the [Google Play Store](https://play.google.com/store/apps/details?id=com.github.gotify) or from [F-Droid](https://f-droid.org/de/packages/com.github.gotify/).
- **iOS**: You can use the third-party client [iGotify Assistant](https://github.com/androidseb25/iGotify-Notification-Assistent).

## Author

Developed by Gemini CLI and Isaac Johnson.

- **Blog**: [freshbrewed.science](https://freshbrewed.science/)
- **LinkedIn**: [isaacinmn](https://www.linkedin.com/in/isaacinmn/)
- **GitHub**: [idjohnson](https://github.com/idjohnson/)
- **Mastodon**: [@Ijohnson](https://noc.social/@Ijohnson)
- **Email**: isaac@freshbrewed.science
