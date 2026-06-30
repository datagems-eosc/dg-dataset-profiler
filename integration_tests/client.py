"""A thin HTTP client over the Dataset Profiler API for the integration tests."""
import time

import requests

from integration_tests import config

# Terminal job states returned by GET /profiler/job_status (see job_storing.JobStatus).
TERMINAL_STATES = {"heavy_profile_ready", "failed", "cleaned_up"}


class ProfilerClient:
    """Wraps the handful of API calls the integration tests need."""

    def __init__(self, base_url: str = config.BASE_URL, token: str = config.AUTH_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def health(self) -> dict:
        resp = self.session.get(self._url("/monitoring/health-check"), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def trigger_profile(self, request_body: dict) -> str:
        """Submit a profiling job and return its job_id."""
        resp = self.session.post(
            self._url("/profiler/trigger_profile"), json=request_body, timeout=30
        )
        resp.raise_for_status()
        return resp.json()["job_id"]

    def job_status(self, job_id: str) -> str:
        resp = self.session.get(self._url(f"/profiler/job_status/{job_id}"), timeout=30)
        resp.raise_for_status()
        return resp.json()["status"]

    def get_profile(self, job_id: str) -> dict:
        resp = self.session.get(self._url(f"/profiler/profile/{job_id}"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def cdd_profile_path(self, dataset_id: str) -> str | None:
        resp = self.session.get(
            self._url(f"/profiler/cdd_profile_path/{dataset_id}"), timeout=30
        )
        resp.raise_for_status()
        return resp.json()["cdd_profile_path"]

    def wait_for_completion(
        self,
        job_id: str,
        timeout: float = config.JOB_TIMEOUT_SECONDS,
        poll_interval: float = config.POLL_INTERVAL_SECONDS,
    ) -> str:
        """Poll job_status until a terminal state is reached or the timeout elapses.

        Returns the final status string. Raises TimeoutError if the job did not
        finish in time.
        """
        deadline = time.monotonic() + timeout
        status = None
        while time.monotonic() < deadline:
            status = self.job_status(job_id)
            if status in TERMINAL_STATES:
                return status
            time.sleep(poll_interval)
        raise TimeoutError(
            f"Job {job_id} did not finish within {timeout}s (last status: {status})"
        )
