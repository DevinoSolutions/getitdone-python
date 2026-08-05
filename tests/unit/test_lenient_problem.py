"""A problem-shaped body that fails strict validation must still be usable.

/v1 may add problem codes additively. An SDK that dropped the whole document on
an unknown code would hide the `request_id` — the one thing support needs.
"""

from __future__ import annotations

from getitdone_py.errors import parse_problem


def test_a_partial_problem_document_never_raises_on_attribute_access():
    problem = parse_problem('{"code":"internal_error","status":500}')
    assert problem is not None
    assert problem.code == "internal_error"
    assert problem.status == 500
    assert problem.title == "internal_error"
    assert problem.type == "about:blank"
    assert problem.detail is None
    assert problem.request_id == ""
    assert problem.errors is None


def test_an_unknown_code_keeps_the_documents_other_fields():
    problem = parse_problem(
        '{"type":"https://x/y","title":"Teapot","status":418,'
        '"code":"i_am_a_teapot","request_id":"req_9","detail":"short and stout"}'
    )
    assert problem is not None
    assert problem.code == "i_am_a_teapot"
    assert problem.title == "Teapot"
    assert problem.request_id == "req_9"
    assert problem.detail == "short and stout"


def test_field_errors_survive_the_lenient_path_when_they_are_well_formed():
    problem = parse_problem(
        '{"code":"future_validation_code","status":400,'
        '"errors":[{"pointer":"/title","code":"too_small","message":"nope"},'
        '{"garbage":true}]}'
    )
    assert problem is not None
    assert problem.errors is not None
    assert len(problem.errors) == 1
    assert problem.errors[0].pointer == "/title"


def test_extra_keys_on_an_unknown_problem_are_preserved():
    problem = parse_problem('{"code":"new_code","status":400,"retry_hint":"later"}')
    assert problem is not None
    assert problem.model_dump()["retry_hint"] == "later"
