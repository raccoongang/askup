from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Provides a tokens generation functionality for the registration email.
    """

    def _make_hash_value(self, user, timestamp):
        """
        Make a hash by user parameters.
        """
        return '{0}{1}{2}'.format(
            six.text_type(user.pk),
            six.text_type(timestamp),
            six.text_type(user.profile.email_confirmed),
        )


account_activation_token = AccountActivationTokenGenerator()
