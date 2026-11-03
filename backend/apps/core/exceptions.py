from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

CODES_BY_STATUS = {403: "permission_denied", 404: "not_found"}


def api_exception_handler(exc, context):
    """Returns every API error as {"error": {"code", "message", "fields"?}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        fields = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
        error = {
            "code": "validation_error",
            "message": _("Please correct the errors and try again."),
            "fields": fields,
        }
    else:
        error = {
            "code": getattr(
                exc, "default_code", CODES_BY_STATUS.get(response.status_code, "error")
            ),
            "message": response.data.get("detail", ""),
        }

    response.data = {"error": error}
    return response
