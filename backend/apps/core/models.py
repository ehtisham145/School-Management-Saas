# Every model is linked to a school for multi-tenancy. Subclasses inherit
# school, created_at, updated_at automatically — see TenantMiddleware for how
# the current school is resolved per request.
from django.db import models


class TenantModel(models.Model):
    school = models.ForeignKey("tenancy.School", on_delete=models.PROTECT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
