"""
Core Role Management System for GramaCart

This module is the SINGLE SOURCE OF TRUTH for role handling.
Uses Django Groups as backend.
Designed for Future scalability (Hub Manager, Support, etc.)
"""

from django.contrib.auth.models import Group

# =========================================================
# ROLE CONSTANTS (DO NOT CHANGE IN CODE ANYWHERE ELSE)
# =========================================================

class Roles:
    ADMIN = "Admin"
    HUB_PARTNER = "HubPartner"
    DELIVERY_BOY = "DeliveryBoy"

    #Future Roles (Not Active yet)
    #SUPPORT_MANAGER = "SupportManager"
    # HUB_MANAGER = "HubManager"


# =========================================================
# CORE ROLE CHECK FUNCTION
# =========================================================

def has_role(user, role_name: str) -> bool:
    """
    Generic role checker.
    Always use this instead of direct group queries.
    """
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name=role_name).exists()


# =========================================================
# SPECIFIC ROLE HELPERS (CLEAN & READABLE)
# =========================================================

def is_admin(user) -> bool:
    return user.is_superuser or has_role(user, Roles.ADMIN)


def is_hub_partner(user) -> bool:
    return has_role(user, Roles.HUB_PARTNER)


def is_delivery_boy(user) -> bool:
    return has_role(user, Roles.DELIVERY_BOY)

#for future scope if we want add the new roles 
# def is_hub_manager(user) -> bool:
#     return has_role(user, Roles.HUB_MANAGER)

# def is_support_manager(user) -> bool:
#     return has_role(user, Roles.SUPPORT_MANAGER)


# =========================================================
# ROLE RESOLVER (FOR UI / DASHBOARD SWITCHING)
# =========================================================

def get_primary_role(user) -> str:
    """
    Returns the first matched role in priority order.
    Used for dashboard routing + sidebar rendering.
    """

    if not user or not user.is_authenticated:
        return "Guest"

    #superuser always admin for now
    if user.is_superuser:
        return Roles.ADMIN

    # priority order matters
    role_priority = [
        Roles.ADMIN,
        Roles.HUB_PARTNER,
        Roles.DELIVERY_BOY,
        # for future scope
        # Roles.HUB_MANAGER,
        # Roles.SUPPORT_MANAGER,
    ]

    user_groups = set(user.groups.values_list("name", flat=True))

    for role in role_priority:
        if role in user_groups:
            return role

    return "User"


# =========================================================
# ROLE VALIDATION (FUTURE SAFETY LAYER)
# =========================================================

def user_has_any_role(user) -> bool:
    """
    Checks if user has at least one valid system role.
    """
    if not user or not user.is_authenticated:
        return False

    return user.groups.exists()


# =========================================================
# ROLE LIST (FOR ADMIN UI / DEBUGGING)
# =========================================================

def get_user_roles(user):
    """
    Returns all roles assigned to user.
    Useful for admin panel or debugging.
    """
    if not user or not user.is_authenticated:
        return []

    return list(user.groups.values_list("name", flat=True))