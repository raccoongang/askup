import hashlib
import logging

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import models
from django.db.models import fields
import shortuuid

log = logging.getLogger(__name__)


def short_token():
    """
    Generate a hash that can be used as lti consumer key.
    """
    hash = hashlib.sha1(shortuuid.uuid().encode())
    hash.update(settings.SECRET_KEY.encode())
    return hash.hexdigest()[::2]


class LtiProvider(models.Model):
    """
    Model to manage LTI consumers.

    LMS connections.
    Automatically generates key and secret for consumers.
    """

    consumer_name = models.CharField(max_length=255, unique=True)
    consumer_key = models.CharField(max_length=32, unique=True, default=short_token)
    consumer_secret = models.CharField(max_length=32, unique=True, default=short_token)

    class Meta:
        verbose_name = "LMS Platform"
        verbose_name_plural = "LMS Platforms"

    def __str__(self):
        """
        Return string representation of the LTIProvider.
        """
        return '<LtiProvider: {}>'.format(self.consumer_name)


class LtiUser(models.Model):
    """
    Model to manage LTI users.
    """

    user_id = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, blank=True, null=True)
    lti_consumer = models.ForeignKey('LtiProvider')
    askup_user = models.ForeignKey(User, blank=True, null=True, related_name='lti_user', on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = "LTI User"
        verbose_name_plural = "LTI Users"
        unique_together = ('lti_consumer', 'user_id')

    def __str__(self):
        """
        Return string representation of the LTIUser.
        """
        return '<LtiUser: {}>'.format(self.user_id)

    @property
    def is_askup_user(self):
        """
        Return boolean flag showing whether LTIUser is connected with UskUp User.
        """
        return bool(self.askup_user)

    def is_registered_to_organization(self, organization):
        """
        Return boolean flag showing whether UskUp User is registered to the organization.

        :param organization: Organization object to check registration.
        :return: boolean flag.
        """
        return self.askup_user.qset_set.filter(pk=organization.pk).exists()

    def lti_to_askup_user(self):
        """
        Connect LTI user with the AskUp user account.
        """
        askup_user, _ = User.objects.get_or_create(username=self.user_id)
        self.askup_user = askup_user
        self.save()

    def add_organization_to_lti_user(self, organization):
        """
        Register user into the required organization.

        :param organization: Organization user is registered to.
        """
        self.askup_user.qset_set.add(organization)
        self.askup_user.save()

    def login(self, request):
        """
        Login connected AskUp user.
        """
        if self.askup_user:
            self.askup_user.backend = 'django.contrib.auth.backends.ModelBackend'
            log.debug("Start User {} login process...".format(self.askup_user.username))
            login(request, self.askup_user)
            log.debug("Check User is authenticated: {}".format(request.user.is_authenticated()))
