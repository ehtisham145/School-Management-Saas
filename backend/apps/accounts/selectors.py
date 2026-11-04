from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.tenancy.models import Membership


def has_confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def must_use_2fa(user):
    return (
        user.is_platform_admin
        or Membership.objects.filter(
            user=user,
            role=Membership.Role.SCHOOL_ADMIN,
            status=Membership.Status.ACTIVE,
            school__is_active=True,
        ).exists()
    )


def needs_2fa_setup(user):
    return must_use_2fa(user) and not has_confirmed_totp(user)
