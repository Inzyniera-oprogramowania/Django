from rest_framework import permissions

class IsAdvancedUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (hasattr(request.user, 'advanced_profile') or request.user.is_staff)
        )
