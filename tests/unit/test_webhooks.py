"""Standard Webhooks verification.

The cross-language vectors in ``tests/fixtures/webhook_vectors.json`` were
produced by IMPORTING the TypeScript producer
(``packages/api-contracts/src/webhooks/signing.ts``) and running it — not by a
Python re-implementation. If the Python verifier accepts them, it is
byte-compatible with the service that signs real deliveries.
"""

from __future__ import annotations

import base64
import binascii
import json

import pytest

from getitdone_py.webhooks import (
    WEBHOOK_DELIVERY_STATES,
    WEBHOOK_EVENT_TYPES,
    WEBHOOK_SIGNATURE_TOLERANCE_SECONDS,
    sign_webhook_payload,
    verify_webhook,
)
from tests.helpers import load_fixture

VECTOR_FILE = load_fixture("webhook_vectors")
VECTORS = VECTOR_FILE["vectors"]
VECTORS_BY_NAME = {vector["name"]: vector for vector in VECTORS}


def now_for(vector: dict) -> int:
    """A clock inside the tolerance window for this vector."""
    return vector["timestamp_seconds"] + 5


def test_the_vector_file_really_came_from_the_typescript_producer():
    assert VECTOR_FILE["producer"] == "packages/api-contracts/src/webhooks/signing.ts"
    assert VECTOR_FILE["producer_revision"] != "unknown"
    assert len(VECTORS) >= 3


@pytest.mark.parametrize("name", sorted(VECTORS_BY_NAME))
def test_a_signature_from_the_typescript_producer_verifies(name: str):
    vector = VECTORS_BY_NAME[name]
    result = verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    )
    assert result.valid is True, f"{name}: {result.reason}"
    assert bool(result) is True


@pytest.mark.parametrize("name", sorted(VECTORS_BY_NAME))
def test_verification_works_on_raw_bytes_as_well_as_str(name: str):
    vector = VECTORS_BY_NAME[name]
    result = verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"].encode("utf-8"),
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    )
    assert result.valid is True


def test_a_unicode_body_verifies_proving_utf8_parity_with_the_producer():
    vector = VECTORS_BY_NAME["task_archived_unicode_body"]
    assert "😀" in vector["raw_body"] or "\\ud83d" in vector["raw_body"]
    assert verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_a_secret_without_the_whsec_prefix_is_decoded_as_is():
    vector = VECTORS_BY_NAME["secret_without_whsec_prefix"]
    assert not vector["secrets"][0].startswith("whsec_")
    assert verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_the_vector_secrets_actually_exercise_the_base64url_alphabet():
    """Without `-`/`_` in the material the vectors could not tell base64url from
    plain base64 — the gotcha this whole fixture exists to pin."""
    for vector in VECTORS:
        for secret in vector["secrets"]:
            material = secret.removeprefix("whsec_")
            assert "-" in material and "_" in material


def test_the_whsec_key_is_base64url_decoded_not_plain_base64():
    """The producer derives the HMAC key with Node's `base64url`, NOT the plain
    base64 the Standard Webhooks reference implementation uses. Strict plain
    base64 cannot even decode this material, so a verifier that reached for
    `b64decode` would fail on every real delivery."""
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    material = vector["secrets"][0].removeprefix("whsec_")

    with pytest.raises(binascii.Error):
        base64.b64decode(material + "=" * (-len(material) % 4), validate=True)

    key_bytes = base64.urlsafe_b64decode(material + "=" * (-len(material) % 4))
    assert key_bytes[:3] == b"\xfb\xff\xbe"

    # And the producer-signed vector verifies with exactly that derivation.
    assert verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


class TestSecretRotation:
    """A mid-rotation delivery carries one `v1,<sig>` entry per active secret."""

    vector = VECTORS_BY_NAME["task_updated_rotation_two_secrets"]

    def test_the_producer_emitted_two_signature_entries(self):
        assert len(self.vector["headers"]["webhook-signature"].split()) == 2

    @pytest.mark.parametrize("secret_index", [0, 1])
    def test_either_rotation_secret_alone_verifies(self, secret_index: int):
        assert verify_webhook(
            headers=self.vector["headers"],
            raw_body=self.vector["raw_body"],
            secret=self.vector["secrets"][secret_index],
            now_seconds=now_for(self.vector),
        ).valid

    def test_passing_both_secrets_verifies(self):
        assert verify_webhook(
            headers=self.vector["headers"],
            raw_body=self.vector["raw_body"],
            secret=self.vector["secrets"],
            now_seconds=now_for(self.vector),
        ).valid

    def test_an_unrelated_secret_does_not_verify(self):
        result = verify_webhook(
            headers=self.vector["headers"],
            raw_body=self.vector["raw_body"],
            secret="whsec_" + base64.urlsafe_b64encode(b"not-the-secret").decode(),
            now_seconds=now_for(self.vector),
        )
        assert result.valid is False
        assert result.reason == "signature_mismatch"


def test_a_tampered_body_is_rejected():
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    payload = json.loads(vector["raw_body"])
    payload["data"]["title"] = "Ship the Python SDK (tampered)"

    result = verify_webhook(
        headers=vector["headers"],
        raw_body=json.dumps(payload),
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    )
    assert result.valid is False
    assert result.reason == "signature_mismatch"


def test_reserializing_an_untouched_body_still_breaks_the_signature():
    """The documented raw-bytes rule, proven: parse + re-dump changes the bytes."""
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    reserialized = json.dumps(json.loads(vector["raw_body"]))  # adds spaces after separators
    assert reserialized != vector["raw_body"]

    assert not verify_webhook(
        headers=vector["headers"],
        raw_body=reserialized,
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_a_tampered_webhook_id_is_rejected():
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {**vector["headers"], "webhook-id": "evt_attacker"}
    result = verify_webhook(
        headers=headers,
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    )
    assert result.reason == "signature_mismatch"


@pytest.mark.parametrize("offset", [301, 3600, -301, -86400])
def test_a_timestamp_outside_the_tolerance_is_rejected(offset: int):
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    result = verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=vector["timestamp_seconds"] + offset,
    )
    assert result.valid is False
    assert result.reason == "timestamp_out_of_tolerance"


@pytest.mark.parametrize("offset", [0, 300, -300])
def test_a_timestamp_on_the_tolerance_boundary_is_accepted(offset: int):
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    assert verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=vector["timestamp_seconds"] + offset,
    ).valid


def test_the_tolerance_is_overridable():
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    assert verify_webhook(
        headers=vector["headers"],
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=vector["timestamp_seconds"] + 3600,
        tolerance_seconds=7200,
    ).valid


def test_the_documented_tolerance_is_five_minutes():
    assert WEBHOOK_SIGNATURE_TOLERANCE_SECONDS == 300
    assert VECTOR_FILE["tolerance_seconds"] == WEBHOOK_SIGNATURE_TOLERANCE_SECONDS


@pytest.mark.parametrize(
    "timestamp",
    ["", "not-a-number", "17850000.5", "-1785000000", "1e9", " "],
)
def test_a_malformed_timestamp_is_rejected(timestamp: str):
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {**vector["headers"], "webhook-timestamp": timestamp}
    result = verify_webhook(
        headers=headers, raw_body=vector["raw_body"], secret=vector["secrets"][0]
    )
    assert result.reason == "malformed_timestamp"


@pytest.mark.parametrize(
    "signature",
    [
        "",
        "   ",
        "no-comma-here",
        "v2,YWJj",
        "v1,",
        "v1,!!!not-base64!!!",
        "v1,YWJj extra-without-comma",
    ],
)
def test_a_malformed_signature_header_is_rejected(signature: str):
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {**vector["headers"], "webhook-signature": signature}
    result = verify_webhook(
        headers=headers,
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    )
    assert result.valid is False
    assert result.reason == "malformed_signature_header"


@pytest.mark.parametrize("missing", ["webhook-id", "webhook-timestamp", "webhook-signature"])
def test_a_missing_required_header_is_rejected(missing: str):
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {k: v for k, v in vector["headers"].items() if k != missing}
    result = verify_webhook(
        headers=headers, raw_body=vector["raw_body"], secret=vector["secrets"][0]
    )
    assert result.reason == "malformed_signature_header"


def test_headers_are_matched_case_insensitively():
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {key.title(): value for key, value in vector["headers"].items()}
    assert "Webhook-Id" in headers
    assert verify_webhook(
        headers=headers,
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_multi_value_headers_from_a_wsgi_style_mapping_work():
    vector = VECTORS_BY_NAME["task_created_single_secret"]
    headers = {key: [value] for key, value in vector["headers"].items()}
    assert verify_webhook(
        headers=headers,
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_httpx_style_header_objects_work():
    import httpx

    vector = VECTORS_BY_NAME["task_created_single_secret"]
    assert verify_webhook(
        headers=httpx.Headers(vector["headers"]),
        raw_body=vector["raw_body"],
        secret=vector["secrets"][0],
        now_seconds=now_for(vector),
    ).valid


def test_the_signer_round_trips_with_the_verifier():
    secret = "whsec_" + base64.urlsafe_b64encode(b"round-trip-secret").decode()
    body = '{"hello":"world"}'
    headers = sign_webhook_payload(
        webhook_id="evt_rt", timestamp_seconds=1785000000, raw_body=body, secrets=[secret]
    )
    assert headers["webhook-id"] == "evt_rt"
    assert headers["webhook-timestamp"] == "1785000000"
    assert headers["webhook-signature"].startswith("v1,")
    assert verify_webhook(
        headers=headers, raw_body=body, secret=secret, now_seconds=1785000000
    ).valid


def test_the_frozen_event_and_delivery_vocabularies():
    assert WEBHOOK_EVENT_TYPES == ("task.created", "task.updated", "task.archived")
    assert WEBHOOK_DELIVERY_STATES == (
        "PENDING",
        "DELIVERING",
        "SUCCEEDED",
        "FAILED",
        "DISABLED",
    )


def test_the_event_vocabulary_matches_the_spec():
    from tests.helpers import load_spec

    spec_events = load_spec()["components"]["schemas"]["WebhookEndpointEventType"]["enum"]
    assert set(WEBHOOK_EVENT_TYPES) == set(spec_events)


def test_the_delivery_state_vocabulary_matches_the_spec():
    from tests.helpers import load_spec

    spec_states = load_spec()["components"]["schemas"]["WebhookDeliveryState"]["enum"]
    assert set(WEBHOOK_DELIVERY_STATES) == set(spec_states)


def test_secret_generation_is_not_shipped():
    """Secret generation stays server-side; only verification is published."""
    import getitdone_py.webhooks as module

    assert not any("generate" in name.lower() for name in module.__all__)
