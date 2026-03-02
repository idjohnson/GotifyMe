import requests
import logging
from typing import Any

logger = logging.getLogger(__name__)

class GotifyClient:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.client_token = None # The token used to manage apps (C...)
        self.app_token = None    # The token used to send messages (A...)
        self.app_name = "FastAPI_Notify_App"

    def setup_token(self) -> None:
        """
        Ensures we have a valid application token.
        Strategy:
        1. Try to list apps using password as X-Gotify-Key (Client Token).
        2. If that fails, try Basic Auth (User/Pass).
        3. Once authenticated, find/create app and get App Token.
        """
        auth_method = None # 'token' or 'basic'
        apps = []
        last_error = None

        # Try using password as Client Token
        try:
            resp = requests.get(
                f"{self.base_url}/application",
                headers={"X-Gotify-Key": self.password},
                timeout=10
            )
            if resp.status_code == 200:
                auth_method = 'token'
                self.client_token = self.password
                apps = resp.json()
                logger.info("Authentication successful (method 1).")
        except requests.RequestException as e:
            logger.debug(f"Auth attempt (method 1) failed: {e}")
            last_error = e

        # If token failed, try Basic Auth
        if not auth_method:
            try:
                resp = requests.get(
                    f"{self.base_url}/application",
                    auth=(self.username, self.password),
                    timeout=10
                )
                if resp.status_code == 200:
                    auth_method = 'basic'
                    apps = resp.json()
                    logger.info("Authenticated using Basic Auth.")
                else:
                    logger.warning(f"Basic Auth failed: {resp.status_code} {resp.text}")
            except requests.RequestException as e:
                logger.error(f"Connection failed: {e}")
                raise

        if not auth_method:
            if last_error:
                raise ValueError("Authentication failed. Check username/password or token.") from last_error
            raise ValueError("Authentication failed. Check username/password or token.")

        # Now we have the list of apps. Find ours or create it.
        # Note: If we used Client Token, we can see existing tokens.
        # If we used Basic Auth, we can also see existing tokens.
        
        target_app = next((app for app in apps if app['name'] == self.app_name), None)

        if target_app:
            self.app_token = target_app['token']
            logger.info(f"Found existing app '{self.app_name}'.")
        else:
            # Create new app
            headers = {}
            auth = None
            if auth_method == 'token':
                headers["X-Gotify-Key"] = self.client_token
            else:
                auth = (self.username, self.password)

            create_resp = requests.post(
                f"{self.base_url}/application",
                headers=headers,
                auth=auth,
                json={"name": self.app_name, "description": "Containerized Notification App"},
                timeout=10
            )
            create_resp.raise_for_status()
            data = create_resp.json()
            self.app_token = data['token']
            logger.info(f"Created new app '{self.app_name}'.")

    def send_notification(self, title: str, message: str, priority: int = 5) -> dict[str, Any]:
        if not self.app_token:
            raise ValueError("App Token not set. Call setup_token() first.")

        try:
            resp = requests.post(
                f"{self.base_url}/message",
                headers={"X-Gotify-Key": self.app_token},
                json={
                    "title": title,
                    "message": message,
                    "priority": priority
                },
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to send notification: {e}")
            raise
