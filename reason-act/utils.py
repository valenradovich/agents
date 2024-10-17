from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.auth.transport.requests import Request
import json
from datetime import datetime, timezone

class AutoRefreshingCredentials(OAuth2Credentials):
    def __init__(self, token_path, scopes):
        self.token_path = token_path
        self._scopes = scopes
        self._load_credentials()
        super().__init__(
            token=self._token,
            refresh_token=self._refresh_token,
            id_token=self._id_token,
            token_uri=self._token_uri,
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=self._scopes
        )

    def _load_credentials(self):
        with open(self.token_path, 'r') as token_file:
            token_data = json.load(token_file)
        self._token = token_data.get('token')
        self._parse_expiry(token_data.get('expiry'))
        self._refresh_token = token_data.get('refresh_token')
        self._id_token = token_data.get('id_token')
        self._token_uri = token_data.get('token_uri')
        self._client_id = token_data.get('client_id')
        self._client_secret = token_data.get('client_secret')

    def _parse_expiry(self, expiry_str):
        if expiry_str:
            try:
                self.expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    self.expiry = datetime.strptime(expiry_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    print(f"Warning: Unable to parse expiry date: {expiry_str}")
                    self.expiry = None
        else:
            self.expiry = None

    def refresh(self, request):
        super().refresh(request)
        self._save_credentials()

    def _save_credentials(self):
        token_data = {
            'token': self.token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': self._scopes,
            'expiry': self.expiry.isoformat() if self.expiry else None,
        }
        with open(self.token_path, 'w') as token_file:
            json.dump(token_data, token_file)