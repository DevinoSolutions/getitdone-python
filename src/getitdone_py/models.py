# GENERATED FILE — DO NOT EDIT.
# Produced by scripts/regenerate-models.sh from openapi/v1.json (the artifact
# the GetItDone server generates from the SAME zod schemas its handlers
# validate with). Edit the server schema and re-run the script instead.
# ruff: noqa

from __future__ import annotations

from datetime import date as _Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class CreateProjectBody(BaseModel):
    """
    Fields for creating a project.
    """

    name: str = Field(
        ...,
        description='Display name, 1-200 characters after trimming.',
        examples=['Website redesign'],
        max_length=200,
        min_length=1,
    )
    description: str | None = Field(
        None,
        description='Optional free-text description (max 2000 characters).',
        max_length=2000,
        min_length=1,
    )


class CreateApiKeyBody(BaseModel):
    """
    Fields for minting a new API key.
    """

    name: str = Field(
        ...,
        description='Caller-given label for the key.',
        examples=['CI deploy bot'],
        max_length=200,
        min_length=1,
    )
    scopes: (
        list[
            Literal[
                'workspaces:read',
                'tasks:read',
                'tasks:write',
                'members:read',
                'projects:read',
                'projects:write',
                'usage:read',
                'api-keys:manage',
                'webhooks:read',
                'webhooks:write',
            ]
        ]
        | None
    ) = Field(
        None,
        description='Subset of scopes to grant. Defaults to every scope EXCEPT `api-keys:manage` — key-minting is never granted by default and must be requested explicitly.',
    )
    test_mode: bool | None = Field(
        None,
        description='Mint a `gid_test_…` sandbox-prefixed key instead of a live one.',
    )
    expires_in_days: int | None = Field(
        None,
        description='Expiry in days from now (1-365). Omit for no expiry.',
        ge=1,
        le=365,
    )


class UpdateTaskBody(BaseModel):
    """
    Partial update — omitted fields keep their current value. Exactly the field set the external MCP `update_task` tool supports; `description`, project links and the parent are not updatable here (the shared update operation carries them over unchanged).
    """

    title: str | None = Field(None, max_length=500, min_length=1)
    status: (
        Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] | None
    ) = Field(None, description='Task workflow status.')
    priority: Literal['LOW', 'MEDIUM', 'HIGH', 'URGENT'] | None = Field(
        None, description='Task priority level.'
    )
    start_date: _Date | None = Field(
        None,
        description='New start date (defer-until) as YYYY-MM-DD (interpreted as UTC). Cannot be cleared — the shared update operation treats absence as "keep".',
    )
    due_date: _Date | None = Field(
        None,
        description='New due date as YYYY-MM-DD (interpreted as UTC). Cannot be cleared — the shared update operation treats absence as "keep".',
    )
    notes: str | None = Field(None, max_length=100000)
    story_points: float | None = Field(None, ge=0.0, le=1000.0)


class SetTaskOccurrenceStatusBody(BaseModel):
    """
    The new state for this one day of the series.
    """

    status: Literal['COMPLETED', 'SKIPPED'] = Field(
        ...,
        description='`COMPLETED` = the work for that day is done (records the completion instant and actor). `SKIPPED` = it will not be done and the day is closed rather than rolled over.',
    )


class AddTaskDependencyBody(BaseModel):
    """
    The blocker to record for the task in the path.
    """

    blocker_task_id: str = Field(
        ...,
        description='The task that must finish FIRST. It must be in the same organization as the task in the path.',
        examples=['T-123'],
        pattern='^(?:T-)?[0-9]{1,12}$',
    )


class CreateDailyPlanEntryBody(BaseModel):
    """
    Which task, which date, which section.
    """

    date: _Date = Field(
        ...,
        description='Board date as YYYY-MM-DD (UTC day).',
    )
    task_id: str = Field(
        ...,
        description='Task short id, e.g. `T-123` (a bare `123` is also accepted on input).',
        examples=['T-123'],
        pattern='^(?:T-)?[0-9]{1,12}$',
    )
    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )


class MoveDailyPlanEntryBody(BaseModel):
    """
    The target section.
    """

    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )


class CreateAttachmentBody(BaseModel):
    """
    Phase 2 of the two-phase upload: register the uploaded file on the task.
    """

    file_name: str = Field(..., max_length=255, min_length=1)
    file_key: str = Field(
        ...,
        description='The `file_key` returned by the upload endpoint.',
        max_length=1024,
        min_length=1,
    )
    content_type: str = Field(..., max_length=255, min_length=1)
    size: int = Field(
        ..., description='File size in bytes as uploaded.', ge=1, le=9007199254740991
    )


class CreateAttachmentUploadBody(BaseModel):
    """
    What you are about to upload.
    """

    file_name: str = Field(
        ..., examples=['screenshot.png'], max_length=255, min_length=1
    )
    content_type: str = Field(..., examples=['image/png'], max_length=255, min_length=1)
    size: int = Field(
        ...,
        description="File size in bytes — checked against the organization's plan file-size and storage allowances.",
        ge=1,
        le=9007199254740991,
    )


class UpdateWebhookEndpointBody(BaseModel):
    """
    Partial update — only send the fields you want to change; at least one is required.
    """

    url: str | None = Field(
        None,
        description='New destination URL, re-validated the same way as create. Changing the URL to a DIFFERENT value resets `verified` to false — the new destination must be re-verified.',
        max_length=2048,
        min_length=1,
    )
    event_types: (
        list[Literal['task.created', 'task.updated', 'task.archived']] | None
    ) = Field(None, description='Replaces the full subscribed-type set.')
    enabled: bool | None = Field(
        None,
        description='Enable or disable delivery. Disabling holds every delivery already queued for the endpoint (they are not sent while it is disabled). Re-enabling (false → true) clears any prior auto-disable reason and resets the consecutive-failure counter; deliveries held while it was off then resume.',
    )


class CreateWebhookEndpointTestEventBody(BaseModel):
    """
    Optional choice of which sample event type to send.
    """

    event_type: Literal['task.created', 'task.updated', 'task.archived'] | None = Field(
        None, description='Which sample event to send. Defaults to `task.created`.'
    )


class ReplayFailedWebhookDeliveriesBody(BaseModel):
    """
    Time window for the bulk replay.
    """

    since: datetime = Field(
        ...,
        description='Only FAILED/DISABLED deliveries created at or after this ISO-8601 instant are replayed.',
        examples=['2026-07-24T00:00:00Z'],
    )


class Organization(BaseModel):
    """
    An organization (workspace) — the tenant every task, project and API credential belongs to.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(
        ...,
        description='Stable opaque organization id.',
        examples=['9f6acab2-8f8e-4c7e-9c3a-2f6d0c9e4b11'],
    )
    name: str = Field(..., description='Display name.', examples=['Acme Inc'])
    slug: str = Field(..., description='URL-safe unique slug.', examples=['acme-inc'])
    image_url: str | None = Field(
        ..., description='Logo URL, or null when none is set.'
    )
    created_at: datetime = Field(
        ...,
        description='Creation time, ISO-8601 UTC.',
        examples=['2026-01-15T09:30:00.000Z'],
    )


class FieldError(BaseModel):
    """
    A single field-level validation failure.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    pointer: str = Field(
        ...,
        description='RFC 6901 JSON Pointer to the offending request field.',
        examples=['/name'],
    )
    code: str = Field(
        ...,
        description='Machine-readable per-field validation code.',
        examples=['invalid_type'],
    )
    message: str = Field(..., description='Human-readable explanation for this field.')


class Burst(BaseModel):
    """
    The per-credential burst policy (separate from period quotas; every key/token gets its own window).
    """

    model_config = ConfigDict(
        extra='allow',
    )
    per_minute_limit: int = Field(
        ...,
        description='Requests each individual credential may make per minute before 429 rate_limited.',
        examples=[10],
        ge=-9007199254740991,
        le=9007199254740991,
    )


class UsageMeter(BaseModel):
    """
    Consumption against one plan allowance.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    meter: Literal['api_calls'] = Field(
        ..., description='Which allowance this entry reports.', examples=['api_calls']
    )
    used: int = Field(
        ...,
        description='Units consumed so far in the current period.',
        examples=[27],
        ge=0,
        le=9007199254740991,
    )
    limit: int = Field(
        ...,
        description="The plan's allowance for this meter per period.",
        examples=[50],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    remaining: int = Field(
        ...,
        description='Units left before requests answer 429 quota_exhausted.',
        examples=[23],
        ge=0,
        le=9007199254740991,
    )


class MemberUser(BaseModel):
    """
    The user identity behind a membership row.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='The member user id.')
    email: str = Field(..., description="The member's email address.")
    name: str | None = Field(..., description='Display name, or null when never set.')


class Project(BaseModel):
    """
    A project — a named grouping of tasks within an organization.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable opaque project id.')
    name: str = Field(
        ...,
        description='Display name, unique within the organization.',
        examples=['Website redesign'],
    )
    description: str | None = Field(
        ..., description='Free-text description, or null when unset.'
    )
    created_at: datetime = Field(
        ...,
        description='Creation time, ISO-8601 UTC.',
    )
    updated_at: datetime = Field(
        ...,
        description='Last-modified time, ISO-8601 UTC.',
    )


class LastUsedAt(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='Last time this key authenticated a request, or null.',
    )


class ExpiresAt(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='Expiry time, or null when the key never expires.',
    )


class ApiKey(BaseModel):
    """
    API-key metadata — never the hash or the plaintext secret.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the key row.')
    name: str | None = Field(..., description='Caller-given label.')
    key_prefix: str | None = Field(
        ...,
        description='Non-secret fingerprint prefix shown in key lists (e.g. `gid_ab12`); never the full secret.',
    )
    scopes: list[
        Literal[
            'workspaces:read',
            'tasks:read',
            'tasks:write',
            'members:read',
            'projects:read',
            'projects:write',
            'usage:read',
            'api-keys:manage',
            'webhooks:read',
            'webhooks:write',
        ]
    ] = Field(..., description='Scopes granted to this key.')
    last_used_at: LastUsedAt | None = Field(
        ..., description='Last time this key authenticated a request, or null.'
    )
    expires_at: ExpiresAt | None = Field(
        ..., description='Expiry time, or null when the key never expires.'
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    legacy: bool = Field(
        ...,
        description='True for a pre-migration user-owned key; false for a current org-owned key. Legacy keys are read-only here — mint new keys as non-legacy.',
    )


class CreatedApiKey(BaseModel):
    """
    A freshly minted API key, including its one-time plaintext secret.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the key row.')
    name: str | None = Field(..., description='Caller-given label.')
    key_prefix: str | None = Field(
        ...,
        description='Non-secret fingerprint prefix shown in key lists (e.g. `gid_ab12`); never the full secret.',
    )
    scopes: list[
        Literal[
            'workspaces:read',
            'tasks:read',
            'tasks:write',
            'members:read',
            'projects:read',
            'projects:write',
            'usage:read',
            'api-keys:manage',
            'webhooks:read',
            'webhooks:write',
        ]
    ] = Field(..., description='Scopes granted to this key.')
    last_used_at: LastUsedAt | None = Field(
        ..., description='Last time this key authenticated a request, or null.'
    )
    expires_at: ExpiresAt | None = Field(
        ..., description='Expiry time, or null when the key never expires.'
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    legacy: bool = Field(
        ...,
        description='True for a pre-migration user-owned key; false for a current org-owned key. Legacy keys are read-only here — mint new keys as non-legacy.',
    )
    key: str = Field(
        ...,
        description='The plaintext secret — shown EXACTLY ONCE. Store it now; it cannot be retrieved again.',
        examples=['gid_51f3...redacted'],
    )


class RevokedApiKey(BaseModel):
    """
    Confirmation that a key was revoked and can no longer authenticate.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='The id of the revoked key.')
    legacy: bool = Field(
        ...,
        description='True when the revoked key was a legacy row (soft-revoked); false for a plugin key (deleted).',
    )


class StartDate(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='Start date (defer-until), ISO-8601 UTC, or null. The task is not meant to be worked on before this day.',
    )


class DueDate(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='Due date, ISO-8601 UTC, or null.',
    )


class ByWeekdayItem(RootModel[int]):
    root: int = Field(..., ge=-9007199254740991, le=9007199254740991)


class ByMonthDay(RootModel[int]):
    root: int = Field(
        ...,
        description='MONTHLY only: day of the month, 1-31, clamped to the last day of shorter months (31 lands on Feb 28, or Feb 29 in a leap year). Null otherwise.',
        ge=-9007199254740991,
        le=9007199254740991,
    )


class EndDate(RootModel[str]):
    root: str = Field(
        ...,
        description='The calendar day the occurrence is for, as YYYY-MM-DD in the recurrence timezone.',
        examples=['2026-08-06'],
        pattern='^\\d{4}-\\d{2}-\\d{2}$',
    )


class MaxOccurrences(RootModel[int]):
    root: int = Field(
        ...,
        description='Total number of occurrences the schedule stops after (RRULE COUNT), or null.',
        ge=-9007199254740991,
        le=9007199254740991,
    )


class StartDate1(RootModel[datetime]):
    root: datetime = Field(
        ...,
    )


class DueDate1(RootModel[datetime]):
    root: datetime = Field(
        ...,
    )


class TaskHistoryEntry(BaseModel):
    """
    One immutable content snapshot from a task's version history — the ONE place versions surface on this API.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(
        ...,
        description='Opaque version identifier — read-only; accepted nowhere else on this API.',
    )
    title: str
    description: str | None = None
    status: Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] = Field(
        ..., description='Task workflow status.'
    )
    priority: Literal['LOW', 'MEDIUM', 'HIGH', 'URGENT'] | None = None
    start_date: StartDate1 | None = None
    due_date: DueDate1 | None = None
    notes: str | None = None
    story_points: float | None = None
    created_at: datetime = Field(
        ...,
        description='When this version was written, ISO-8601 UTC.',
    )


class CompletedAt(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='The INSTANT the user completed this day, ISO-8601 UTC, or null. Deliberately distinct from `occurrence_date`: completing Tuesday on Monday records both truths.',
    )


class TaskOccurrence(BaseModel):
    """
    One DAY of a repeating task, with its own completion state.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    task_id: str = Field(
        ..., description="The repeating task's short id.", examples=['T-123']
    )
    occurrence_date: str = Field(
        ...,
        description='The calendar day the occurrence is for, as YYYY-MM-DD in the recurrence timezone.',
        examples=['2026-08-06'],
        pattern='^\\d{4}-\\d{2}-\\d{2}$',
    )
    sequence: int = Field(
        ...,
        description='1-based ordinal of this day within the series — what an RRULE COUNT limit and streak math count.',
        examples=[12],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    status: Literal['PENDING', 'COMPLETED', 'SKIPPED', 'MISSED'] = Field(
        ...,
        description='Per-day state of one occurrence of a repeating task. `PENDING` is written by materialization and `MISSED` by the rollover sweep — only `COMPLETED` and `SKIPPED` are user-written.',
    )
    completed_at: CompletedAt | None = Field(
        ...,
        description='The INSTANT the user completed this day, ISO-8601 UTC, or null. Deliberately distinct from `occurrence_date`: completing Tuesday on Monday records both truths.',
    )


class TaskDependencyRef(BaseModel):
    """
    A task on the other end of a dependency link.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    task_id: str = Field(
        ...,
        description='Task short id, e.g. `T-123` (a bare `123` is also accepted on input).',
        examples=['T-123'],
        pattern='^(?:T-)?[0-9]{1,12}$',
    )
    title: str = Field(
        ...,
        description="The other task's title (its current version).",
        examples=['Ship the public API'],
    )
    status: Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] = Field(
        ..., description='Task workflow status.'
    )
    open: bool = Field(
        ...,
        description='Whether this task is still outstanding — not COMPLETED and not archived. Only OPEN blockers hold work back, so this is the flag `is_blocked` aggregates.',
    )


class DailyPlanEntry(BaseModel):
    """
    One task pinned onto one daily-board section.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(
        ...,
        description='Board-entry id. NOTE: moving an entry between sections re-creates it (mirroring the in-app move), so the id CHANGES on move.',
    )
    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )
    task_id: str = Field(
        ..., description="The planned task's short id.", examples=['T-123']
    )
    title: str = Field(..., description="The planned task's current title.")
    status: Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] = Field(
        ..., description="The planned task's current workflow status."
    )
    created_at: datetime = Field(
        ...,
        description='When the task was placed on this section, ISO-8601 UTC. Entries within a section are ordered by this (oldest first) — there is no free positional reorder.',
    )


class DailyPlanStatus(BaseModel):
    """
    One section's fill-status for one date.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    date: _Date = Field(
        ...,
    )
    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )
    status: Literal['COMPLETED', 'PLANNED', 'NOT_FILLED', 'FILLING'] = Field(
        ..., description='Fill-state of one daily-board section for one date.'
    )


class DeletedDailyPlanEntry(BaseModel):
    """
    Acknowledgement of a removed board entry.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str
    deleted: Literal[True]


class Attachment(BaseModel):
    """
    A file attached to a task's current version. Fetch its bytes via the `download-url` endpoint.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable opaque attachment id.')
    file_name: str = Field(..., examples=['screenshot.png'])
    content_type: str = Field(..., examples=['image/png'])
    size: int = Field(
        ...,
        description='File size in bytes.',
        ge=-9007199254740991,
        le=9007199254740991,
    )
    created_at: datetime = Field(
        ...,
    )


class AttachmentUpload(BaseModel):
    """
    Phase 1 of the two-phase upload: where to PUT the file.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    upload_url: str = Field(
        ...,
        description='Presigned URL — PUT the raw file bytes here (Content-Type must match what you declared).',
    )
    upload_method: Literal['PUT']
    file_key: str = Field(
        ...,
        description='Opaque storage key; pass it back when registering the attachment after the upload succeeds.',
    )
    expires_at: datetime = Field(
        ...,
        description='When the upload URL stops working, ISO-8601 UTC.',
    )


class AttachmentDownloadUrl(BaseModel):
    """
    A short-lived presigned download URL.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    url: str = Field(..., description='Presigned GET URL.')
    expires_at: datetime = Field(
        ...,
        description='When the URL stops working, ISO-8601 UTC.',
    )


class WebhookEndpoint(BaseModel):
    """
    A webhook endpoint configuration — NEVER includes the signing secret (shown once, at creation/rotation).
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the endpoint.')
    url: str = Field(..., description='The https destination URL.')
    enabled: bool = Field(
        ...,
        description='False when disabled — manually, auto-disabled after repeated delivery failures, or paused when the account that set it up had its email address verified (see `disabled_reason`). A disabled endpoint receives nothing: deliveries already queued for it are held, not sent, and go out only if it is re-enabled.',
    )
    event_types: list[Literal['task.created', 'task.updated', 'task.archived']] = Field(
        ..., description='Subscribed event types. An EMPTY array means "every type".'
    )
    verified: bool = Field(
        ...,
        description='True once the `verify` action has proven this endpoint accepts a correctly-signed request.',
    )
    disabled_reason: str | None = Field(
        ...,
        description='Why the endpoint was auto-disabled or paused by an account take-back, or null when it never was.',
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    updated_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )


class CreatedWebhookEndpoint(BaseModel):
    """
    A freshly registered endpoint, including its one-time signing secret. Starts UNVERIFIED — call the `verify` action to prove ownership before relying on deliveries.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the endpoint.')
    url: str = Field(..., description='The https destination URL.')
    enabled: bool = Field(
        ...,
        description='False when disabled — manually, auto-disabled after repeated delivery failures, or paused when the account that set it up had its email address verified (see `disabled_reason`). A disabled endpoint receives nothing: deliveries already queued for it are held, not sent, and go out only if it is re-enabled.',
    )
    event_types: list[Literal['task.created', 'task.updated', 'task.archived']] = Field(
        ..., description='Subscribed event types. An EMPTY array means "every type".'
    )
    verified: bool = Field(
        ...,
        description='True once the `verify` action has proven this endpoint accepts a correctly-signed request.',
    )
    disabled_reason: str | None = Field(
        ...,
        description='Why the endpoint was auto-disabled or paused by an account take-back, or null when it never was.',
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    updated_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    secret: str = Field(
        ...,
        description='The signing secret (`whsec_…`) — shown EXACTLY ONCE. Store it now; it cannot be retrieved again, only rotated. Note: replaying this exact request within the 24h Idempotency-Key window returns this SAME secret again — treat a stored Idempotency-Key as equally sensitive to the secret itself.',
        examples=['whsec_51f3...redacted'],
    )


class DeletedWebhookEndpoint(BaseModel):
    """
    Confirmation that the endpoint — and every pending/queued delivery for it — was permanently deleted.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='The id of the deleted endpoint.')


class RotatedWebhookEndpointSecret(BaseModel):
    """
    Result of a create-overlap-revoke secret rotation. Rotating a SECOND time before the first rotation's grace window elapses immediately drops the FIRST previous secret — there is only ever one previous-secret slot, not a stack.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the endpoint.')
    url: str = Field(..., description='The https destination URL.')
    enabled: bool = Field(
        ...,
        description='False when disabled — manually, auto-disabled after repeated delivery failures, or paused when the account that set it up had its email address verified (see `disabled_reason`). A disabled endpoint receives nothing: deliveries already queued for it are held, not sent, and go out only if it is re-enabled.',
    )
    event_types: list[Literal['task.created', 'task.updated', 'task.archived']] = Field(
        ..., description='Subscribed event types. An EMPTY array means "every type".'
    )
    verified: bool = Field(
        ...,
        description='True once the `verify` action has proven this endpoint accepts a correctly-signed request.',
    )
    disabled_reason: str | None = Field(
        ...,
        description='Why the endpoint was auto-disabled or paused by an account take-back, or null when it never was.',
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    updated_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )
    secret: str = Field(
        ...,
        description='The NEW signing secret — shown EXACTLY ONCE.',
        examples=['whsec_51f3...redacted'],
    )
    previous_secret_expires_at: datetime = Field(
        ...,
        description='The prior secret keeps signing outgoing deliveries alongside the new one until this time (~24h out) — dual-secret acceptance so you can finish updating your verifier before the old secret dies.',
    )


class WebhookEndpointVerificationResult(BaseModel):
    """
    Result of a live, synchronous verification probe. A failure does NOT unset a previously-earned verified state — only a success ever (re)sets it.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    verified: bool = Field(
        ...,
        description="True when the endpoint answered the signed test request with a 2xx status. On true, the endpoint's verified state is set.",
    )
    status: int | None = Field(
        None,
        description='The HTTP status the endpoint returned, when a response was received at all (absent for a blocked/timed-out/network-failed probe).',
        ge=-9007199254740991,
        le=9007199254740991,
    )
    reason: str | None = Field(
        None, description='Present when `verified` is false — why the probe failed.'
    )


class LastStatus(RootModel[int]):
    root: int = Field(
        ...,
        description='HTTP status of the most recent attempt, or null before any attempt has run.',
        ge=-9007199254740991,
        le=9007199254740991,
    )


class NextAttemptAt(RootModel[datetime]):
    root: datetime = Field(
        ...,
        description='When the next retry is scheduled, or null when not PENDING.',
    )


class WebhookDelivery(BaseModel):
    """
    One delivery-log row — REDACTED: never includes response bodies or the signing secret.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the delivery row.')
    event_id: str = Field(
        ...,
        description="The owning WebhookEvent's id — also the `webhook-id` signature header on the wire.",
    )
    event_type: str = Field(..., description='The domain event type.')
    state: Literal['PENDING', 'DELIVERING', 'SUCCEEDED', 'FAILED', 'DISABLED'] = Field(
        ..., description='Lifecycle state of one (event, endpoint) delivery.'
    )
    attempt_count: int = Field(
        ...,
        description='Number of delivery attempts made so far.',
        ge=-9007199254740991,
        le=9007199254740991,
    )
    last_status: LastStatus | None = Field(
        ...,
        description='HTTP status of the most recent attempt, or null before any attempt has run.',
    )
    next_attempt_at: NextAttemptAt | None = Field(
        ..., description='When the next retry is scheduled, or null when not PENDING.'
    )
    created_at: datetime = Field(
        ...,
        description='ISO-8601 UTC.',
    )


class ReplayedWebhookDeliveries(BaseModel):
    """
    Result of a bulk replay of failed deliveries.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    replayed_count: int = Field(
        ...,
        description='How many FRESH PENDING deliveries this call created (capped at 1000 per call).',
        ge=-9007199254740991,
        le=9007199254740991,
    )


class CreateTaskBody(BaseModel):
    """
    Fields for creating a task.
    """

    title: str = Field(
        ...,
        description='Task title, 1-500 characters after trimming.',
        examples=['Ship the public API'],
        max_length=500,
        min_length=1,
    )
    description: str | None = Field(None, max_length=10000)
    status: (
        Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] | None
    ) = Field(None, description='Initial status (defaults to TODO).')
    priority: Literal['LOW', 'MEDIUM', 'HIGH', 'URGENT'] | None = Field(
        None, description='Task priority level.'
    )
    start_date: _Date | None = Field(
        None,
        description='Start date (defer-until) as YYYY-MM-DD (interpreted as UTC).',
    )
    due_date: _Date | None = Field(
        None,
        description='Due date as YYYY-MM-DD (interpreted as UTC).',
    )
    notes: str | None = Field(None, max_length=100000)
    story_points: float | None = Field(None, ge=0.0, le=1000.0)
    project_id: str | None = Field(
        None,
        description="Link the new task to this project (must belong to the credential's organization).",
    )
    parent_task_id: str | None = Field(
        None,
        description="Create as a subtask of this task (short id, must belong to the credential's organization).",
        examples=['T-123'],
        pattern='^(?:T-)?[0-9]{1,12}$',
    )


class SetDailyPlanStatusBody(BaseModel):
    """
    Which section, and its new status.
    """

    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )
    status: Literal['COMPLETED', 'PLANNED', 'NOT_FILLED', 'FILLING'] = Field(
        ..., description='Fill-state of one daily-board section for one date.'
    )


class CreateWebhookEndpointBody(BaseModel):
    """
    Fields for registering a new webhook endpoint.
    """

    url: str = Field(
        ...,
        description='The https destination URL. Must be https, port 443 (explicit or default), and carry no `user:pass@` credentials — a URL failing this check answers 422 `webhook_url_rejected` with the specific reason and creates NO row.',
        examples=['https://example.com/webhooks/getitdone'],
        max_length=2048,
        min_length=1,
    )
    event_types: (
        list[Literal['task.created', 'task.updated', 'task.archived']] | None
    ) = Field(
        None,
        description='Subset of event types to subscribe to. Omit or send an empty array to subscribe to every type.',
    )
    enabled: bool | None = Field(None, description='Defaults to true.')


class OrganizationList(BaseModel):
    """
    Cursor-envelope page of organizations.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[Organization] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class Problem(BaseModel):
    """
    RFC 9457 problem document with the GetItDone `code` extension.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    type: str = Field(
        ...,
        description='URI identifying the problem class; resolves to its docs page.',
        examples=['https://nowgetitdone.com/docs/api/problems/validation-failed'],
    )
    title: str = Field(
        ...,
        description='Short human-readable summary of the problem class. Never parse it — switch on `code`.',
    )
    status: int = Field(
        ...,
        description='HTTP status code, duplicated from the response.',
        examples=[400],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    detail: str | None = Field(
        None, description='Human-readable explanation specific to this occurrence.'
    )
    code: Literal[
        'missing_credentials',
        'invalid_api_key',
        'invalid_token',
        'insufficient_scope',
        'feature_not_enabled',
        'validation_failed',
        'resource_not_found',
        'rate_limited',
        'quota_exhausted',
        'idempotency_key_missing',
        'idempotency_key_reused',
        'idempotency_in_progress',
        'webhook_url_rejected',
        'delivery_already_pending',
        'dependency_cycle',
        'internal_error',
    ] = Field(
        ...,
        description='Stable machine-readable problem code — the value SDKs branch on.',
    )
    request_id: str = Field(
        ...,
        description='The x-request-id of the failing request — quote it in support requests.',
    )
    errors: list[FieldError] | None = Field(
        None, description='Field-level failures (present on validation_failed).'
    )


class Usage(BaseModel):
    """
    The organization's consumption against its plan for the current billing period, plus the burst policy.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    plan: Literal['FREE', 'PRO', 'TEAM'] = Field(
        ..., description="The organization's current plan tier.", examples=['FREE']
    )
    period_start: datetime = Field(
        ...,
        description='Start of the current billing period, ISO-8601 UTC. Paid plans anchor at their subscription renewal; free plans at the first of the calendar month.',
        examples=['2026-07-01T00:00:00.000Z'],
    )
    period_end: datetime = Field(
        ...,
        description='End of the current billing period, ISO-8601 UTC — when period meters reset.',
        examples=['2026-08-01T00:00:00.000Z'],
    )
    meters: list[UsageMeter] = Field(
        ..., description='Per-meter consumption for the current period.'
    )
    burst: Burst = Field(
        ...,
        description='The per-credential burst policy (separate from period quotas; every key/token gets its own window).',
    )


class Member(BaseModel):
    """
    One membership row — a user attached to this organization.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(..., description='Stable id of the membership row itself.')
    user: MemberUser
    role: str = Field(
        ..., description="The member's role in the organization.", examples=['owner']
    )
    created_at: datetime = Field(
        ...,
        description='When this membership was created, ISO-8601 UTC.',
    )


class ProjectList(BaseModel):
    """
    Cursor-envelope page of an organization's projects.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[Project] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class ApiKeyList(BaseModel):
    """
    Cursor-envelope page of the organization's API keys.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[ApiKey] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class TaskRecurrence(BaseModel):
    """
    A task's repeat schedule. Each day is completed independently through the task-occurrence operations.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    frequency: Literal['DAILY', 'WEEKLY', 'MONTHLY'] = Field(
        ...,
        description='How often a repeating task recurs — the RRULE `FREQ` this rule projects to.',
    )
    interval: int = Field(
        ...,
        description='Repeat every N units of `frequency` — 2 with WEEKLY is "every other week".',
        examples=[1],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    by_weekday: list[ByWeekdayItem] = Field(
        ...,
        description='WEEKLY only: the weekdays it falls on, 0 = Sunday through 6 = Saturday (`[1,2,3,4,5]` is "every weekday"). Empty for DAILY and MONTHLY.',
    )
    by_month_day: ByMonthDay | None = Field(
        ...,
        description='MONTHLY only: day of the month, 1-31, clamped to the last day of shorter months (31 lands on Feb 28, or Feb 29 in a leap year). Null otherwise.',
    )
    basis: Literal['SCHEDULE', 'AFTER_COMPLETION'] = Field(
        ...,
        description='Whether the next day is measured from the calendar (`SCHEDULE`) or from the day the previous occurrence was completed (`AFTER_COMPLETION`).',
    )
    timezone: str = Field(
        ...,
        description='IANA timezone whose CALENDAR DAYS the occurrences fall on.',
        examples=['America/Toronto'],
    )
    start_date: str = Field(
        ...,
        description='First day the task may recur (RRULE DTSTART). No occurrence is ever created before it.',
        examples=['2026-08-06'],
        pattern='^\\d{4}-\\d{2}-\\d{2}$',
    )
    end_date: EndDate | None = Field(
        ...,
        description='Last day the task may recur (RRULE UNTIL), or null for a schedule with no end date.',
    )
    max_occurrences: MaxOccurrences | None = Field(
        ...,
        description='Total number of occurrences the schedule stops after (RRULE COUNT), or null.',
    )
    rollover_enabled: bool = Field(
        ...,
        description='When true, an unfinished occurrence keeps surfacing on later days instead of silently vanishing.',
    )
    active: bool = Field(
        ...,
        description='False once the schedule was stopped (cleared, series completed, or task archived). Past occurrences are KEPT either way — completion history is never rewritten.',
    )
    rrule: str = Field(
        ...,
        description='RFC 5545 projection of the fields above, derived on read — never stored, never accepted on input.',
        examples=['FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'],
    )


class TaskHistoryList(BaseModel):
    """
    Cursor-envelope page of task versions, newest first.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[TaskHistoryEntry] = Field(
        ..., description='The current page of results.'
    )
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class TaskOccurrenceList(BaseModel):
    """
    Cursor-envelope page of occurrences, most recent day first. A task that does not repeat answers an empty page.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[TaskOccurrence] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class TaskDependencies(BaseModel):
    """
    Both directions of a task's blocker graph, one hop out, plus its derived blocked state.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    task_id: str = Field(
        ...,
        description='The task this view is for.',
        examples=['T-123'],
        pattern='^(?:T-)?[0-9]{1,12}$',
    )
    is_blocked: bool = Field(
        ...,
        description="DERIVED on every read: true when at least one entry in `blocked_by` is still `open`. Never a stored column and never written to the task's `status` — a blocked task keeps whatever status its owner set.",
    )
    blocked_by_count: int = Field(
        ...,
        description='How many tasks must finish first, open or not — `blocked_by.length`.',
        examples=[2],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    blocking_count: int = Field(
        ...,
        description='How many tasks wait on this one — `blocking.length`.',
        examples=[1],
        ge=-9007199254740991,
        le=9007199254740991,
    )
    blocked_by: list[TaskDependencyRef] = Field(
        ...,
        description='Tasks that must finish before this one can be worked on, oldest link first.',
    )
    blocking: list[TaskDependencyRef] = Field(
        ...,
        description='Tasks waiting on this one, oldest link first — the other direction of the same edges.',
    )


class DailyPlanSection(BaseModel):
    """
    One section of the user's board for one date.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    section: Literal['TODO', 'PROGRESS'] = Field(
        ...,
        description='Daily-board section: `TODO` = the plan list, `PROGRESS` = the in-progress list.',
    )
    status: Literal['COMPLETED', 'PLANNED', 'NOT_FILLED', 'FILLING'] = Field(
        ..., description='Fill-state of one daily-board section for one date.'
    )
    entries: list[DailyPlanEntry] = Field(
        ..., description='Entries in placement order (oldest first).'
    )


class AttachmentList(BaseModel):
    """
    Cursor-envelope page of the task's current-version attachments.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[Attachment] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class WebhookEndpointList(BaseModel):
    """
    Cursor-envelope page of the organization's webhook endpoints.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[WebhookEndpoint] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class WebhookEndpointTestEventResult(BaseModel):
    """
    Result of a synchronous, signed sample-event delivery. This is a LIVE probe — it does not create a queued WebhookDelivery row, so it never appears in the delivery log.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    outcome: Literal[
        'delivered', 'blocked', 'redirect_blocked', 'request_failed', 'timeout'
    ] = Field(..., description='The immediate outcome of the synchronous test POST.')
    status: int | None = Field(
        None,
        description='The HTTP status returned, when a response was received.',
        ge=-9007199254740991,
        le=9007199254740991,
    )
    duration_ms: int = Field(
        ...,
        description='Wall-clock time the probe took.',
        ge=-9007199254740991,
        le=9007199254740991,
    )


class WebhookDeliveryList(BaseModel):
    """
    Cursor-envelope page of one endpoint's delivery log.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[WebhookDelivery] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class MemberList(BaseModel):
    """
    Cursor-envelope page of an organization's members.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[Member] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )


class Task(BaseModel):
    """
    A task, projected from its stable identity plus its CURRENT version.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    id: str = Field(
        ...,
        description='The task short id — the ONE public task identifier.',
        examples=['T-123'],
    )
    title: str = Field(..., examples=['Ship the public API'])
    description: str | None = Field(
        ..., description='Free-text description, or null when unset.'
    )
    status: Literal['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'] = Field(
        ..., description='Task workflow status.'
    )
    priority: Literal['LOW', 'MEDIUM', 'HIGH', 'URGENT'] | None = None
    start_date: StartDate | None = Field(
        ...,
        description='Start date (defer-until), ISO-8601 UTC, or null. The task is not meant to be worked on before this day.',
    )
    due_date: DueDate | None = Field(
        ..., description='Due date, ISO-8601 UTC, or null.'
    )
    notes: str | None = Field(
        ..., description='Rich-text notes of the current version, or null.'
    )
    story_points: float | None = None
    project_ids: list[str] = Field(
        ...,
        description='Ids of the projects the CURRENT version is linked to (a task can belong to several).',
    )
    parent_task_id: str | None = Field(
        ...,
        description="The parent task's short id when this is a subtask, else null.",
        examples=['T-99'],
    )
    archived: bool
    recurrence: TaskRecurrence | None = Field(
        ...,
        description='The repeat schedule when this task recurs, else null. Per-day completion lives in the occurrence ledger (`/v1/tasks/{task_id}/occurrences`), never in `status` — completing Monday leaves Tuesday untouched.',
    )
    created_at: datetime = Field(
        ...,
        description='Task creation time (first version), ISO-8601 UTC.',
    )
    updated_at: datetime = Field(
        ...,
        description='Last content change (current version), ISO-8601 UTC.',
    )


class DailyPlan(BaseModel):
    """
    The credential user's daily board for one date in the credential's organization.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    date: _Date = Field(
        ...,
        description='The board date (UTC day).',
    )
    sections: list[DailyPlanSection] = Field(
        ..., description='Always both sections: TODO then PROGRESS.'
    )


class TaskList(BaseModel):
    """
    Cursor-envelope page of tasks, most recently updated first.
    """

    model_config = ConfigDict(
        extra='allow',
    )
    data: list[Task] = Field(..., description='The current page of results.')
    has_more: bool = Field(
        ..., description='True when another page exists after this one.'
    )
    next_cursor: str | None = Field(
        ...,
        description='Opaque cursor for the next page (pass as `after`); null on the last page.',
    )
