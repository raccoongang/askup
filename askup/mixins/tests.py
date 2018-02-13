class LoginAdminByDefaultMixIn(object):
    """Provides a default user login procedure."""

    def default_login(self):
        """Perform a default user login procedure."""
        self.client.login(username='admin', password='admin')
