from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect
from django.urls import reverse


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

        if not request.user.is_authenticated():
            return redirect(reverse('askup:sign_in'))

        return func(*args, **kwargs)

    return wrapper
