"""MathE document endpoints: auth, FileObject lookup, the AP, the cache, Ray and timeouts.

Tokens are real RS256 JWTs signed with a key generated here. The identity
provider's keys, MoMa, Redis and Ray are faked; the files are real, under a
temporary "/s3" mount.
"""

import asyncio
import copy
import shutil
import threading
import time
from types import SimpleNamespace

import httpx
import jwt
import pymupdf
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataset_profiler.document_processing import file_objects, markdown_cache
from dataset_profiler.document_processing.service import ConversionMode, ConvertResult
from dataset_profiler.document_processing.vlm_transcription import TranscriptionError
from dataset_profiler.job_manager import document_job
from dataset_profiler.routes import document_auth, documents

ISSUER = "https://keycloak.test/oauth/realms/dev"
AUDIENCE = "dataset-profiler-api"
PDF = "tests/assets/dummy_data/data/pdfs/960.pdf"   # 3 pages
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

DATASET = "0c9b7e65-2f3a-4d18-b6e4-9a1c5d7e8f12"
OTHER_DATASET = "9d0c1b2a-3e4f-4a5b-8c6d-7e8f9a0b1c2d"
AP_ID = "6f1c2a4e-0b7d-4c1e-9a52-3d1f0e8b7a10"
OPERATOR = "a3e5d9c2-71f4-4b8e-8c0a-5e2b9d4f6c11"
KEYWORDS_OPERATOR = "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
FILE_A = "5b2d8f17-9c4e-4a63-8d1b-7e0f2a6c9d13"
FILE_B = "7c3e9a28-0d5f-4b74-9e2c-8f1a3b7d0e24"


def make_token(roles=("dg_user",), audience=AUDIENCE, issuer=ISSUER, key=SIGNING_KEY,
               expires_in=300):
    claims = {
        "iss": issuer, "aud": audience, "sub": "mathe-backend", "azp": "dg-app-api",
        "exp": int(time.time()) + expires_in, "realm_access": {"roles": list(roles)},
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test"})


def auth(token=None):
    return {"Authorization": f"Bearer {token or make_token()}"}


# --- fakes -------------------------------------------------------------------------

class FakeRedis:
    def __init__(self):
        self.values, self.ttls = {}, {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key], self.ttls[key] = value, ex


class FakeMoMa:
    """MoMa's GET /api/nodes/{id}: nodes by id, and the requests it got."""

    def __init__(self):
        self.nodes, self.calls, self.down = {}, [], False

    def add_pdf(self, node_id, content_url, encoding="application/pdf", **properties):
        self.nodes[node_id] = {"id": node_id, "labels": ["cr:FileObject"], "properties": {
            "contentUrl": content_url, "encodingFormat": encoding, "name": "x.pdf", **properties}}

    def get(self, url, headers, timeout):
        self.calls.append((url, headers))
        if self.down:
            raise requests.ConnectionError("connection refused")
        node = self.nodes.get(url.rsplit("/", 1)[-1])
        return SimpleNamespace(status_code=200 if node else 404, ok=node is not None,
                               json=lambda: node, text="")


class FakeRay:
    """Runs each task in-process when it is submitted; records the submissions."""

    def __init__(self):
        self.submitted, self.finish, self.cancelled = [], True, False
        self.wait_hook = None

    def remote(self, *args):
        self.submitted.append(args)
        return document_job.convert_and_cache(*args)

    def wait(self, refs, num_returns, timeout):
        if self.wait_hook:
            self.wait_hook()
        return (refs, []) if self.finish else ([], refs)

    def get(self, ref):
        return ref

    def cancel(self, ref):
        self.cancelled = True


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """A "/s3" mount holding dataset DATASET with two PDFs, and another dataset."""
    mount = tmp_path / "s3"
    folder = mount / "dataset" / DATASET
    folder.mkdir(parents=True)
    shutil.copy(PDF, folder / "129.pdf")
    other = pymupdf.open()       # different content from 129.pdf
    other.new_page().insert_text((72, 72), "Integration by parts")
    other.save(folder / "130.pdf")
    (folder / "broken.pdf").write_bytes(b"not a pdf at all")
    (mount / "dataset" / OTHER_DATASET).mkdir()
    shutil.copy(PDF, mount / "dataset" / OTHER_DATASET / "secret.pdf")
    monkeypatch.setenv("DOCUMENT_S3_MOUNT", str(mount))
    monkeypatch.setenv("DATA_ROOT_PATH", str(mount / "dataset") + "/")
    return mount


@pytest.fixture
def moma(monkeypatch, storage):
    fake = FakeMoMa()
    fake.add_pdf(FILE_A, f"s3://dataset/{DATASET}/129.pdf", sha256="stale-profile-hash")
    fake.add_pdf(FILE_B, f"/s3/dataset/{DATASET}/130.pdf")
    monkeypatch.setattr(file_objects.requests, "get", fake.get)
    monkeypatch.setenv("MOMA_API_URL", "https://moma.test/moma2/v1/")
    return fake


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(markdown_cache, "get_redis_client", lambda: fake)
    return fake


@pytest.fixture
def converted(monkeypatch):
    """convert_document, faked: the file's name as Markdown; records the paths."""
    paths = []

    def fake_convert(path, mode):
        paths.append(path)
        return ConvertResult(markdown=f"# {path.rsplit('/', 1)[-1]} Μαθηματικά", pages=3,
                             mode=mode, model="glm-5.3-flash" if mode == "quality" else "")

    monkeypatch.setattr(document_job, "convert_document", fake_convert)
    return paths


@pytest.fixture
def ray(monkeypatch):
    fake = FakeRay()
    monkeypatch.setattr(documents.ray_client, "ensure_connection", lambda: True)
    monkeypatch.setattr(documents, "convert_document_task", fake)
    monkeypatch.setattr(documents, "ray", fake)
    return fake


@pytest.fixture
def app(monkeypatch, moma, redis, converted, ray):
    monkeypatch.setenv("DOCUMENTS_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URL", ISSUER)
    monkeypatch.setenv("OIDC_AUDIENCE", AUDIENCE)
    for name in ("DOCUMENTS_ALLOWED_ROLES", "DOCUMENT_MAX_FILES", "DOCUMENT_MAX_PAGES",
                 "DOCUMENT_REQUEST_TIMEOUT_SECONDS", "DOCUMENT_VLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    keys = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(
        key=SIGNING_KEY.public_key()))
    monkeypatch.setattr(document_auth, "_jwks_client", lambda issuer, verify_ssl: keys)
    application = FastAPI()
    application.include_router(documents.router)
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def make_ap(files=(FILE_A,), mode="quality", dataset=DATASET, file_properties=None):
    """An AP as the Gateway builds it: convert, then keyword matching, one Markdown node per file."""
    nodes = [
        {"id": AP_ID, "labels": ["Analytical_Pattern"], "properties": {"name": "MathE keywords"}},
        {"id": OPERATOR, "labels": ["Document_Convert_Operator", "Operator"],
         "properties": {"name": "Convert", "mode": mode, "startTime": "2026-11-26T10:00:00Z"}},
        {"id": KEYWORDS_OPERATOR, "labels": ["Keyword_Matching_Operator", "Operator"],
         "properties": {"k": 10, "method": "bm25", "candidates": ["integral", "λ"]}},
    ]
    edges = [
        {"from": AP_ID, "to": OPERATOR, "labels": ["consist_of"]},
        {"from": AP_ID, "to": KEYWORDS_OPERATOR, "labels": ["consist_of"]},
        {"from": OPERATOR, "to": KEYWORDS_OPERATOR, "labels": ["follows"]},
    ]
    if dataset:
        nodes.append({"id": dataset, "labels": ["sc:Dataset"]})
    for index, file_id in enumerate(files):
        markdown_id = f"00000000-0000-4000-8000-00000000000{index}"
        keywords_id = f"00000000-0000-4000-9000-00000000000{index}"
        nodes += [
            {"id": file_id, "labels": ["cr:FileObject"], "properties": dict(file_properties or {})},
            {"id": markdown_id, "labels": ["ResultType"],
             "properties": {"name": "markdown", "fileObjectId": file_id}},
            {"id": keywords_id, "labels": ["ResultType"],
             "properties": {"name": "keywords", "fileObjectId": file_id}},
        ]
        edges += [
            {"from": OPERATOR, "to": file_id, "labels": ["input"]},
            {"from": OPERATOR, "to": markdown_id, "labels": ["output"]},
            {"from": KEYWORDS_OPERATOR, "to": markdown_id, "labels": ["input"]},
            {"from": KEYWORDS_OPERATOR, "to": keywords_id, "labels": ["output"]},
        ]
        if dataset:
            edges.append({"from": dataset, "to": file_id, "labels": ["distribution"]})
    return {"ap": {"nodes": nodes, "edges": edges}}


def markdown_node(ap, file_id):
    return next(n for n in ap["ap"]["nodes"]
                if n.get("properties", {}).get("name") == "markdown"
                and n["properties"].get("fileObjectId") == file_id)


def post_ap(client, ap, **kwargs):
    return client.post("/documents/convert4ap", json=ap, headers=kwargs.pop("headers", auth()),
                       **kwargs)


# --- the AP round trip -----------------------------------------------------------------

def test_markdown_nodes_are_filled_and_the_rest_is_unchanged(client):
    sent = make_ap(files=(FILE_A, FILE_B))
    response = post_ap(client, sent)
    assert response.status_code == 200
    returned = response.json()

    for file_id, name in ((FILE_A, "129.pdf"), (FILE_B, "130.pdf")):
        properties = markdown_node(returned, file_id)["properties"]
        assert properties["value"] == f"# {name} Μαθηματικά"
        assert properties["pages"] == 3
        assert properties["model"] == "glm-5.3-flash"
        assert properties["fallbackPages"] == []
        assert len(properties["sha256"]) == 64
        assert "error" not in properties

    # Everything but the Markdown nodes' properties is returned exactly as sent.
    expected = copy.deepcopy(sent)
    for file_id in (FILE_A, FILE_B):
        markdown_node(expected, file_id)["properties"] = markdown_node(returned, file_id)["properties"]
    assert returned == expected
    # Greek is sent as UTF-8, not as \u escapes.
    assert "Μαθηματικά".encode() in response.content


def test_mode_is_read_from_the_operator(client, ray):
    assert post_ap(client, make_ap(mode="fast")).status_code == 200
    assert ray.submitted[0][1] == "fast"
    assert post_ap(client, make_ap()).status_code == 200
    assert ray.submitted[1][1] == "quality"


def test_a_failed_file_is_reported_on_its_node_only(client, monkeypatch, converted):
    real = document_job.convert_document

    def fail_on_130(path, mode):
        if path.endswith("130.pdf"):
            raise TranscriptionError("The vision model could not transcribe any page")
        return real(path, mode)

    monkeypatch.setattr(document_job, "convert_document", fail_on_130)
    returned = post_ap(client, make_ap(files=(FILE_A, FILE_B))).json()
    assert markdown_node(returned, FILE_A)["properties"]["value"].startswith("# 129.pdf")
    failed = markdown_node(returned, FILE_B)["properties"]
    assert failed["error"] == "The vision model could not transcribe any page"
    assert "value" not in failed


def test_internal_errors_are_not_leaked(client, monkeypatch):
    def crash(path, mode):
        raise KeyError("SCAYLE token 0xdeadbeef rejected")

    monkeypatch.setattr(document_job, "convert_document", crash)
    properties = markdown_node(post_ap(client, make_ap()).json(), FILE_A)["properties"]
    assert properties["error"] == "The document could not be converted"


@pytest.mark.parametrize("change, message", [
    (lambda ap: ap["ap"]["nodes"].pop(1), "exactly one Document_Convert_Operator"),
    (lambda ap: ap["ap"].update(edges=[e for e in ap["ap"]["edges"]
                                       if not (e["from"] == OPERATOR and e["labels"] == ["input"])]),
     "no input cr:FileObject"),
    (lambda ap: ap["ap"].update(edges=[e for e in ap["ap"]["edges"]
                                       if not (e["from"] == OPERATOR and e["labels"] == ["output"])]),
     "No Markdown ResultType output node"),
    (lambda ap: ap["ap"]["nodes"][1]["properties"].update(mode="turbo"), "Unknown mode"),
    (lambda ap: ap["ap"]["nodes"].append({"id": OTHER_DATASET, "labels": ["sc:Dataset"]}) or
     ap["ap"]["edges"].append({"from": OTHER_DATASET, "to": FILE_A, "labels": ["distribution"]}),
     "several datasets"),
    (lambda ap: ap.pop("ap"), "under 'ap'"),
])
def test_malformed_ap_is_422(client, change, message):
    ap = make_ap()
    change(ap)
    response = post_ap(client, ap)
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_too_many_files_is_422(client, monkeypatch):
    monkeypatch.setenv("DOCUMENT_MAX_FILES", "1")
    assert post_ap(client, make_ap(files=(FILE_A, FILE_B))).status_code == 422


# --- FileObject lookup -------------------------------------------------------------------

def test_moma_gets_the_callers_token_and_correlation_id(client, moma):
    token = make_token()
    post_ap(client, make_ap(), headers={**auth(token), "x-tracking-correlation": "corr-1"})
    (url, headers), = moma.calls
    assert url == f"https://moma.test/moma2/v1/api/nodes/{FILE_A}"
    assert headers["Authorization"] == f"Bearer {token}"
    assert headers["x-tracking-correlation"] == "corr-1"


def test_s3_and_mounted_content_urls_both_map(client, converted, storage):
    assert post_ap(client, make_ap(files=(FILE_A, FILE_B))).status_code == 200
    folder = storage / "dataset" / DATASET
    assert converted == [str(folder / "129.pdf"), str(folder / "130.pdf")]


def test_a_content_url_in_the_ap_is_ignored(client, converted, storage):
    ap = make_ap(file_properties={"contentUrl": f"s3://dataset/{OTHER_DATASET}/secret.pdf",
                                  "encodingFormat": "application/pdf"})
    assert post_ap(client, ap).status_code == 200
    assert converted == [str(storage / "dataset" / DATASET / "129.pdf")]


@pytest.mark.parametrize("encoding, url", [
    ("text/csv", f"s3://dataset/{DATASET}/129.pdf"),
    ("application/pdf", f"s3://dataset/{DATASET}/notes.csv"),
])
def test_a_non_pdf_is_400(client, moma, encoding, url):
    moma.add_pdf(FILE_A, url, encoding=encoding)
    response = post_ap(client, make_ap())
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


def test_a_node_that_is_no_file_object_is_400(client, moma):
    moma.nodes[FILE_A]["labels"] = ["dg:DatabaseConnection"]
    assert post_ap(client, make_ap()).status_code == 400


def test_unknown_or_hidden_file_object_is_404(client, moma):
    del moma.nodes[FILE_A]
    response = post_ap(client, make_ap())
    assert response.status_code == 404
    assert FILE_A in response.json()["detail"]


def test_moma_unreachable_is_424(client, moma):
    moma.down = True
    assert post_ap(client, make_ap()).status_code == 424


@pytest.mark.parametrize("url", [
    f"s3://dataset/{DATASET}/../{OTHER_DATASET}/secret.pdf",
    f"/s3/dataset/{DATASET}/escape.pdf",          # a symlink out of the dataset storage
    "/etc/passwd.pdf",
    "s3://scratchpad/x.pdf",
    "relative/path.pdf",
])
def test_paths_outside_the_dataset_storage_are_refused(client, moma, storage, tmp_path, url):
    (tmp_path / "outside.pdf").write_bytes(b"%PDF")
    (storage / "dataset" / DATASET / "escape.pdf").symlink_to(tmp_path / "outside.pdf")
    moma.add_pdf(FILE_A, url)
    assert post_ap(client, make_ap()).status_code == 400


def test_a_file_of_another_dataset_is_refused(client, moma):
    moma.add_pdf(FILE_A, f"s3://dataset/{OTHER_DATASET}/secret.pdf")
    response = post_ap(client, make_ap())
    assert response.status_code == 400
    assert DATASET in response.json()["detail"]
    # Without a dataset in the AP, any file of the dataset storage is allowed.
    assert post_ap(client, make_ap(dataset=None)).status_code == 200


def test_missing_file_is_404(client, moma):
    moma.add_pdf(FILE_A, f"s3://dataset/{DATASET}/gone.pdf")
    assert post_ap(client, make_ap()).status_code == 404


def test_unreadable_or_too_long_pdf_is_400(client, moma, monkeypatch):
    moma.add_pdf(FILE_A, f"s3://dataset/{DATASET}/broken.pdf")
    assert post_ap(client, make_ap()).status_code == 400
    moma.add_pdf(FILE_A, f"s3://dataset/{DATASET}/129.pdf")
    monkeypatch.setenv("DOCUMENT_MAX_PAGES", "2")
    response = post_ap(client, make_ap())
    assert response.status_code == 400
    assert "3 pages" in response.json()["detail"]


def test_dataset_storage_not_configured_is_503(client, monkeypatch):
    monkeypatch.delenv("DATA_ROOT_PATH")
    assert post_ap(client, make_ap()).status_code == 503


# --- cache, Ray and time -------------------------------------------------------------------

def test_a_second_request_is_served_from_the_cache(client, ray, redis):
    first = post_ap(client, make_ap()).json()
    assert len(ray.submitted) == 1
    (key, _), = redis.values.items()
    assert key.startswith("document_markdown:") and key.endswith(":quality:glm-5.3-flash")
    assert redis.ttls[key] == 30 * 24 * 3600

    second = post_ap(client, make_ap()).json()
    assert len(ray.submitted) == 1
    assert markdown_node(second, FILE_A) == markdown_node(first, FILE_A)
    # Another mode is another conversion.
    post_ap(client, make_ap(mode="fast"))
    assert len(ray.submitted) == 2


def test_the_same_content_is_converted_once(client, ray, moma):
    moma.add_pdf(FILE_B, f"s3://dataset/{DATASET}/129.pdf")
    returned = post_ap(client, make_ap(files=(FILE_A, FILE_B))).json()
    assert len(ray.submitted) == 1
    assert (markdown_node(returned, FILE_A)["properties"]["value"]
            == markdown_node(returned, FILE_B)["properties"]["value"])


def test_degraded_or_failed_conversions_are_not_cached(client, monkeypatch, redis, ray):
    monkeypatch.setattr(document_job, "convert_document", lambda path, mode: ConvertResult(
        markdown="partly", pages=3, mode=mode, model="glm-5.3-flash", fallback_pages=[2]))
    returned = post_ap(client, make_ap()).json()
    assert markdown_node(returned, FILE_A)["properties"]["fallbackPages"] == [2]
    assert redis.values == {}

    def fail(path, mode):
        raise TranscriptionError("The vision model could not transcribe any page")

    monkeypatch.setattr(document_job, "convert_document", fail)
    post_ap(client, make_ap())
    assert redis.values == {}


def test_redis_down_still_converts(client, monkeypatch, ray):
    def down():
        raise ConnectionError("redis is down")

    monkeypatch.setattr(markdown_cache, "get_redis_client", down)
    assert post_ap(client, make_ap()).status_code == 200
    assert len(ray.submitted) == 1


def test_timeout_is_504_and_the_tasks_keep_running(client, ray):
    ray.finish = False
    response = post_ap(client, make_ap())
    assert response.status_code == 504
    assert "retry later" in response.json()["detail"]
    assert not ray.cancelled


def test_ray_down_is_503(client, monkeypatch, ray):
    monkeypatch.setattr(documents.ray_client, "ensure_connection", lambda: False)
    assert post_ap(client, make_ap()).status_code == 503


def test_cached_files_need_no_ray(client, monkeypatch, ray):
    post_ap(client, make_ap())
    monkeypatch.setattr(documents.ray_client, "ensure_connection", lambda: False)
    assert post_ap(client, make_ap()).status_code == 200


def test_two_requests_are_processed_concurrently(app, ray):
    # Each request waits on Ray until the other one waits too: served one after
    # the other, the first would wait alone and time out.
    barrier = threading.Barrier(2, timeout=5)
    ray.wait_hook = barrier.wait

    async def both():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            return await asyncio.gather(
                http.post("/documents/convert4ap", json=make_ap(files=(FILE_A,)), headers=auth()),
                http.post("/documents/convert4ap", json=make_ap(files=(FILE_B,)), headers=auth()),
            )

    first, second = asyncio.run(both())
    assert first.status_code == second.status_code == 200


# --- the plain endpoint --------------------------------------------------------------------

def test_convert_without_an_ap(client, moma):
    del moma.nodes[FILE_B]
    response = client.post("/documents/convert", headers=auth(), json={
        "fileObjectIds": [FILE_A, FILE_A], "mode": "fast", "datasetId": DATASET})
    assert response.status_code == 200
    (file,) = response.json()["files"]
    assert file["fileObjectId"] == FILE_A
    assert file["markdown"] == "# 129.pdf Μαθηματικά"
    assert file["error"] is None and file["model"] == ""

    response = client.post("/documents/convert", headers=auth(), json={"fileObjectIds": [FILE_B]})
    assert response.status_code == 404


@pytest.mark.parametrize("body", [{}, {"fileObjectIds": []}, {"fileObjectIds": [FILE_A], "mode": "turbo"},
                                  {"fileObjectIds": [FILE_A], "datasetId": "../x"}])
def test_convert_rejects_bad_requests(client, body):
    assert client.post("/documents/convert", headers=auth(), json=body).status_code == 422


# --- authentication ---------------------------------------------------------------------

def test_missing_token_is_401(client):
    response = client.post("/documents/convert4ap", json=make_ap())
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("token", [
    make_token(audience="dataset-recsys-api"),
    make_token(issuer="https://evil.test/realms/dev"),
    make_token(key=OTHER_KEY),
    make_token(expires_in=-60),
    "not-a-jwt",
])
def test_invalid_tokens_are_401(client, token):
    assert post_ap(client, make_ap(), headers=auth(token)).status_code == 401


def test_unsigned_token_is_401(client):
    token = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 60,
                        "realm_access": {"roles": ["dg_admin"]}}, key=None, algorithm="none")
    assert post_ap(client, make_ap(), headers=auth(token)).status_code == 401


def test_missing_role_is_403(client, moma):
    response = post_ap(client, make_ap(), headers=auth(make_token(roles=["offline_access"])))
    assert response.status_code == 403
    assert moma.calls == []


@pytest.mark.parametrize("role", ["user", "dg_user", "dg_system", "dg_admin", "dg_dataset-curator"])
def test_allowed_and_privileged_roles_pass(client, role):
    assert post_ap(client, make_ap(), headers=auth(make_token(roles=[role]))).status_code == 200


def test_allowed_roles_are_configurable(client, monkeypatch):
    monkeypatch.setenv("DOCUMENTS_ALLOWED_ROLES", "mathe_service")
    assert post_ap(client, make_ap(), headers=auth(make_token(roles=["dg_user"]))).status_code == 403
    assert post_ap(client, make_ap(),
                   headers=auth(make_token(roles=["mathe_service"]))).status_code == 200


def test_identity_provider_down_is_503(client, monkeypatch):
    def unreachable(issuer, verify_ssl):
        raise jwt.PyJWKClientConnectionError("connection refused")

    monkeypatch.setattr(document_auth, "_jwks_client", unreachable)
    assert post_ap(client, make_ap()).status_code == 503


def test_auth_can_be_turned_off(client, monkeypatch, moma):
    monkeypatch.setenv("DOCUMENTS_AUTH_ENABLED", "false")
    assert client.post("/documents/convert4ap", json=make_ap()).status_code == 200
    assert "Authorization" not in moma.calls[0][1]


def test_profiler_auth_switch_does_not_open_the_document_endpoints(client, monkeypatch):
    monkeypatch.setenv("ENABLE_AUTH", "false")
    assert client.post("/documents/convert4ap", json=make_ap()).status_code == 401


# --- the Ray task, on its own ----------------------------------------------------------------

def test_the_task_caches_a_good_conversion(redis, converted):
    answer = document_job.convert_and_cache("/s3/dataset/x/a.pdf", "quality", "key-1", FILE_A)
    assert answer["result"]["markdown"] == "# a.pdf Μαθηματικά"
    assert ConvertResult.model_validate_json(redis.values["key-1"]).mode == ConversionMode.QUALITY
