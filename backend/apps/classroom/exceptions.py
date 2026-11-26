from rest_framework.exceptions import APIException


class WorkspaceReadOnly(APIException):
    status_code = 403
    default_code = "workspace_read_only"
    default_detail = "Your trial or plan has ended. Upgrade to make changes."


class PlanLimitReached(APIException):
    status_code = 403
    default_code = "plan_limit_reached"
    default_detail = "You have reached the limit of your plan."


class ProRequired(APIException):
    status_code = 403
    default_code = "pro_required"
    default_detail = "This feature is part of Teacher Pro."


class SchoolPlanOnly(APIException):
    status_code = 403
    default_code = "school_plan_only"
    default_detail = "Classes and parent messages are part of the school plan."


class AiQuotaReached(APIException):
    status_code = 403
    default_code = "ai_quota_reached"
    default_detail = "You have used all your AI lesson plans for this month."


class AiExamQuotaReached(APIException):
    status_code = 403
    default_code = "ai_exam_quota_reached"
    default_detail = "You have used all your AI tests for this period."


class RegenerateLimitReached(APIException):
    status_code = 403
    default_code = "regenerate_limit_reached"
    default_detail = "You can't write any more new questions for this draft."


class InputRejected(APIException):
    """A file or choice that can't be used. `code` tells the app which message to show."""

    status_code = 400

    def __init__(self, code, detail):
        super().__init__(detail, code)
        # The error handler reads default_code, so each instance carries its own.
        self.default_code = code


class ServiceUnavailable(APIException):
    status_code = 503
    default_code = "service_unavailable"
    default_detail = "This service is not available right now. Please try again later."
