from rest_framework.exceptions import APIException

MESSAGES = {
    "browser_agent_disabled": (403, "The browser agent is not available yet."),
    "browser_agent_budget_reached": (
        503,
        "The browser agent has reached its limit for this month. Please try again next month.",
    ),
    "task_already_running": (
        409,
        "You already have a task running. Wait for it to finish or cancel it first.",
    ),
    "browser_agent_busy": (503, "The browser agent is busy right now. Please try again soon."),
    "workspace_read_only": (403, "Your trial or plan has ended. Upgrade to make changes."),
    "consent_required": (403, "Please read and accept the Lesson Lab Agent notice first."),
    "agent_quota_reached": (
        403,
        "You have used all your Lesson Lab Agent tasks. Choose a plan to get more.",
    ),
    "goal_required": (400, "Please describe the task."),
    "goal_too_long": (400, "Please describe the task in fewer words."),
    "start_url_scheme": (
        400,
        "The start page must be a web address starting with http or https.",
    ),
}


class AgentError(APIException):
    """One error per code, so the app can show the right message in either language."""

    def __init__(self, code):
        status, message = MESSAGES.get(code, (400, "This request can't be done."))
        super().__init__(message, code)
        self.status_code = status
        # The project's error handler reads default_code.
        self.default_code = code
