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


class AiQuotaReached(APIException):
    status_code = 403
    default_code = "ai_quota_reached"
    default_detail = "You have used all your AI lesson plans for this month."


class ServiceUnavailable(APIException):
    status_code = 503
    default_code = "service_unavailable"
    default_detail = "This service is not available right now. Please try again later."
