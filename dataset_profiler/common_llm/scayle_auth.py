import requests
from typing import Optional, List, Dict, Any


class ScayleAuthClient:
    """Authenticate with Scayle and provide OpenAI-compatible API access details."""

    #: Cap on how long establishing the TCP connection may take. ``requests``
    #: applies a scalar timeout to the connect phase as well, so a long read
    #: timeout would otherwise make an unreachable host (VPN down, wrong host)
    #: hang for that full duration before failing.
    DEFAULT_CONNECT_TIMEOUT = 10.0

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str,
        verify_ssl: bool = True,
        timeout: float = 30.0,
        connect_timeout: Optional[float] = None,
    ):
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.connect_timeout = (
            self.DEFAULT_CONNECT_TIMEOUT if connect_timeout is None else connect_timeout
        )
        self._api_key: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def _request_timeout(self) -> tuple:
        """``(connect, read)`` timeout pair for outgoing requests."""
        return (min(self.connect_timeout, self.timeout), self.timeout)

    def authenticate(self, force_refresh: bool = False) -> str:
        if self._api_key is not None and not force_refresh:
            return self._api_key

        response = requests.post(
            f"{self.base_url}/v1/auths/ldap",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"user": self.username, "password": self.password},
            verify=self.verify_ssl,
            timeout=self._request_timeout,
        )

        if response.status_code != 200:
            raise ValueError(
                f"Scayle authentication failed with status {response.status_code}: {response.text}"
            )

        payload = response.json()
        token = payload.get("token")
        if not token:
            raise ValueError(
                "Scayle authentication succeeded but no token was returned"
            )

        self._api_key = token
        return token

    def list_models(self) -> List[str]:
        token = self.authenticate()
        response = requests.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {token}"},
            verify=self.verify_ssl,
            timeout=self._request_timeout,
        )

        if response.status_code != 200:
            raise ValueError(
                f"Scayle model listing failed with status {response.status_code}: {response.text}"
            )

        payload: Dict[str, Any] = response.json()
        model_entries = payload.get("data", [])
        return [
            entry["id"]
            for entry in model_entries
            if isinstance(entry, dict) and "id" in entry
        ]

    def check_connection(self) -> bool:
        try:
            response = requests.get(
                self.base_url,
                allow_redirects=True,
                verify=self.verify_ssl,
                timeout=min(10.0, self.timeout),
            )
            return response.status_code > 0
        except Exception:
            return False
