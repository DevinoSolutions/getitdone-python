"""Resource namespaces — one module per ``/v1`` resource family."""

from __future__ import annotations

from getitdone_py.resources.api_keys import ApiKeys, AsyncApiKeys
from getitdone_py.resources.attachments import AsyncAttachments, Attachments
from getitdone_py.resources.daily_plan import AsyncDailyPlan, DailyPlan
from getitdone_py.resources.members import AsyncMembers, Members
from getitdone_py.resources.organizations import AsyncOrganizations, Organizations
from getitdone_py.resources.projects import AsyncProjects, Projects
from getitdone_py.resources.tasks import AsyncTasks, Tasks
from getitdone_py.resources.usage import AsyncUsage, Usage
from getitdone_py.resources.webhook_endpoints import AsyncWebhookEndpoints, WebhookEndpoints

__all__ = [
    "ApiKeys",
    "AsyncApiKeys",
    "AsyncAttachments",
    "AsyncDailyPlan",
    "AsyncMembers",
    "AsyncOrganizations",
    "AsyncProjects",
    "AsyncTasks",
    "AsyncUsage",
    "AsyncWebhookEndpoints",
    "Attachments",
    "DailyPlan",
    "Members",
    "Organizations",
    "Projects",
    "Tasks",
    "Usage",
    "WebhookEndpoints",
]
