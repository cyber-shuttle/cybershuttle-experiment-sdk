import time

import requests


class DeviceFlowAuthenticator:

    client_id: str
    realm: str
    auth_server_url: str
    device_code: str | None
    interval: int
    access_token: str | None
    refresh_token: str | None

    @property
    def logged_in(self) -> bool:
        return self.access_token is not None

    def __init__(
        self,
        client_id: str,
        realm: str,
        auth_server_url: str,
    ):
        self.client_id = client_id
        self.realm = realm
        self.auth_server_url = auth_server_url

        if not self.client_id or not self.realm or not self.auth_server_url:
            raise ValueError("Missing required environment variables for client ID, realm, or auth server URL")

        self.device_code = None
        self.interval = -1
        self.access_token = None

    def login(self, interactive: bool = True):
        # Step 1: Request device and user code
        auth_device_url = f"{self.auth_server_url}/realms/{self.realm}/protocol/openid-connect/auth/device"
        response = requests.post(auth_device_url, data={"client_id": self.client_id, "scope": "openid"})

        if response.status_code != 200:
            print(f"Error in device authorization request: {response.status_code} - {response.text}")
            return

        data = response.json()
        self.device_code = data.get("device_code")
        self.interval = data.get("interval", 5)

        print(f"User code: {data.get('user_code')}")
        print(f"Please authenticate by visiting: {data.get('verification_uri_complete')}")

        if interactive:
            import webbrowser

            webbrowser.open(data.get("verification_uri_complete"))

        # Step 2: Poll for the token
        self.__poll_for_token__()

    def logout(self):
        self.access_token = None
        self.refresh_token = None

    def __poll_for_token__(self):
        token_url = f"{self.auth_server_url}/realms/{self.realm}/protocol/openid-connect/token"
        print("Waiting for authorization...")
        while True:
            response = requests.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": self.device_code,
                },
            )
            if response.status_code == 200:
                data = response.json()
                self.refresh_token = data.get("refresh_token")
                self.access_token = data.get("access_token")
                print("Authorization successful!")
                return
            elif response.status_code == 400 and response.json().get("error") == "authorization_pending":
                time.sleep(self.interval)
            else:
                print(f"Authorization error: {response.status_code} - {response.text}")
                break
