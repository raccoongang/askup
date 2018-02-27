def client_user(username, password=None):
    """Decorate a TestCase class method to login client by username and password provided."""
    def client_wrapper(func):
        def wrapping_function(*args, **kwargs):
            if username is None:
                args[0].client.logout()
            else:
                args[0].client.login(username=username, password=password)

            result = func(*args, **kwargs)

            if hasattr(args[0], 'default_login'):
                args[0].default_login()

            return result

        return wrapping_function

    return client_wrapper
