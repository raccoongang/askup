import logging

from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect
from django.urls import reverse


log = logging.getLogger(__name__)


def do_redirect_unauthenticated(user):
    """Return redirect in case of unauthenticated user and return False otherwise."""
    if not user.is_authenticated():
        logging.info('Unauthenticated user tried to perform unauthorized action')
        return redirect(reverse('askup:sign_in'))
    else:
        return False


def redirect_unauthenticated(func):
    """
    Decorate a view function to redirect requests of unauthenticated users.

    Can decorate a simple view function as well as dispatch method of generic view class.
    """
    def wrapper(*args, **kwargs):
        if isinstance(args[0], WSGIRequest):
            request = args[0]
        else:
            request = args[0].request

        return do_redirect_unauthenticated(request.user) or func(*args, **kwargs)

    return wrapper


def user_group_required(*required_groups):
    """
    Decorate a view function to check if user belongs to one of the groups passed as an arguments.

    Can decorate a simple view function as well as dispatch method of generic view class.
    """
    def wrapper(func):
        def wrapped_function(*args, **kwargs):
            request = args[0] if isinstance(args[0], WSGIRequest) else args[0].request
            user = request.user
            auth_check_result = do_redirect_unauthenticated(user)

            if auth_check_result:
                return auth_check_result

            if check_user_has_groups(user, required_groups):
                return func(*args, **kwargs)

            return redirect(reverse('askup:organizations'))

        return wrapped_function

    return wrapper


def check_user_has_groups(user, required_groups):
    """Check if user has required groups."""
    if type(required_groups) is str:
        required_groups = [required_groups]

    required_groups_lower = set(name.lower() for name in required_groups)
    user_groups = set(name.lower() for name in user.groups.values_list('name', flat=True))

    if 'admins' in required_groups_lower and user.is_superuser:
        return True

    groups_found = required_groups_lower.intersection(user_groups)

    if groups_found:
        return True

    logging.info('User tried to perform unauthorized action')
    return False
