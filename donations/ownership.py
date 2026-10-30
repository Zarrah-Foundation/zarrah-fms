from django.db.models import Q

from accounts.verification import is_email_verified, user_owns_donation


def donations_for_user(user):
    """Donations owned by FK or matched to verified user email."""
    if not user or not user.is_authenticated:
        return None
    q = Q(user=user)
    if is_email_verified(user) and user.email:
        q |= Q(donor_email__iexact=user.email)
    from donations.models import Donation

    return Donation.objects.filter(q).select_related("category", "transaction").distinct()


def user_can_access_donation(user, donation) -> bool:
    from accounts.models import Role

    if user_owns_donation(user, donation):
        return True
    if user.is_authenticated and (
        user.is_superuser
        or user.role in (Role.SUPER_ADMIN, Role.EXECUTIVE_ADMIN, Role.FINANCE_OFFICER)
    ):
        return True
    return False
