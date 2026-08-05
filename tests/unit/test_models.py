"""The generated models must accept real /v1 payload shapes.

``problem_missing_credentials.json`` is a VERBATIM capture from production
(``GET https://app.nowgetitdone.com/v1/organizations`` with no credentials,
2026-08-05); the rest are built from the vendored spec's own property
examples, so a schema change that breaks these breaks real traffic too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from getitdone_py import models
from tests.helpers import load_fixture, load_spec

MODELS_SOURCE = Path(models.__file__)

FIXTURE_MODELS = [
    ("task", "Task"),
    ("usage", "Usage"),
    ("webhookdelivery", "WebhookDelivery"),
    ("organization", "Organization"),
    ("member", "Member"),
    ("project", "Project"),
    ("apikey", "ApiKey"),
    ("attachment", "Attachment"),
    ("webhookendpoint", "WebhookEndpoint"),
    ("dailyplan", "DailyPlan"),
    ("taskhistoryentry", "TaskHistoryEntry"),
    ("problem_missing_credentials", "Problem"),
]


@pytest.mark.parametrize(("fixture", "model_name"), FIXTURE_MODELS)
def test_fixture_payload_validates_against_generated_model(fixture: str, model_name: str) -> None:
    model = getattr(models, model_name)
    instance = model.model_validate(load_fixture(fixture))
    assert instance is not None


@pytest.mark.parametrize(("fixture", "model_name"), FIXTURE_MODELS)
def test_fixture_payload_round_trips_through_the_model(fixture: str, model_name: str) -> None:
    raw = load_fixture(fixture)
    model = getattr(models, model_name)
    dumped = model.model_validate(raw).model_dump(mode="json", exclude_none=True)
    for key in raw:
        assert key in dumped, f"{model_name}.{key} was dropped on round trip"


def test_every_named_object_schema_has_a_generated_model() -> None:
    spec_schemas = load_spec()["components"]["schemas"]
    assert len(spec_schemas) == 58

    object_schemas = {n for n, s in spec_schemas.items() if s.get("type") == "object"}
    assert len(object_schemas) == 51

    generated = set(vars(models))
    missing = object_schemas - generated
    assert missing == set(), f"object schemas with no generated model: {sorted(missing)}"


def test_string_enum_schemas_are_inlined_as_literal_unions() -> None:
    """The 7 string enums become ``Literal[...]`` at each use site.

    ``--enum-field-as-literal all`` is deliberate: callers pass and match plain
    strings (``status="TODO"``) instead of importing an enum class.
    """
    spec_schemas = load_spec()["components"]["schemas"]
    enum_schemas = {n: s for n, s in spec_schemas.items() if "enum" in s}
    assert set(enum_schemas) == {
        "DailySection",
        "DailyStatus",
        "TaskPriority",
        "TaskStatus",
        "WebhookDeliveryState",
        "WebhookEndpointEventType",
        "WebhookTestEventOutcome",
    }

    source = MODELS_SOURCE.read_text(encoding="utf-8")
    for name, schema in enum_schemas.items():
        for value in schema["enum"]:
            assert f"'{value}'" in source, f"{name} value {value!r} missing from models.py"


def test_real_production_problem_document_parses_with_its_code_and_request_id() -> None:
    problem = models.Problem.model_validate(load_fixture("problem_missing_credentials"))
    assert problem.code == "missing_credentials"
    assert problem.status == 401
    assert problem.request_id == "77362019-9a63-40a9-9113-f87450865384"


def test_unknown_server_fields_survive_instead_of_breaking_the_model() -> None:
    """/v1 evolves additively — a new field must not crash an older SDK."""
    raw = {**load_fixture("task"), "brand_new_server_field": "hello"}
    task = models.Task.model_validate(raw)
    assert task.model_dump()["brand_new_server_field"] == "hello"
