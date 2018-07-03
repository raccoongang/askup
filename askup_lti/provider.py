import logging

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from lti import InvalidLTIRequestError
from lti.contrib.django import DjangoToolProvider
from oauthlib import oauth1

from askup.models import Qset
from .models import LtiProvider, LtiUser
from .validator import SignatureValidator

log = logging.getLogger(__name__)


@csrf_exempt
def lti_launch(request, qset_id=None):
    """
    Endpoint for all requests to embed LMS content via the LTI protocol.

    An LTI launch is successful if:
    - The launch contains all the required parameters
    - The launch data is correctly signed using a known client key/secret pair
    """
    try:
        tool_provider = DjangoToolProvider.from_django_request(request=request)
        validator = SignatureValidator()
        ok = tool_provider.is_valid_request(validator)
    except (oauth1.OAuth1Error, InvalidLTIRequestError, ValueError) as err:
        ok = False
        log.error('Error happened while LTI request: {}'.format(err.__str__()))
    if not ok:
        raise Http404('LTI request is not valid')

    anononcement_page = render(
        request,
        template_name="askup_lti/announcement.html",
        context={
            'title': 'announcement',
            'message': 'coming soon!',
            'tip': 'this subject is about to open.',
        }
    )

    qset = Qset.objects.filter(id=qset_id).first()

    if not qset_id or not qset:
        return anononcement_page

    return student_lti_flow(request, qset)


def student_lti_flow(request, qset):
    """
    Provide LTI flow for the student.

    :param qset: Qset object which need to be shown to the student.
    :return: redirect to the required query set.
    """
    lti_consumer = LtiProvider.objects.get(consumer_key=request.POST['oauth_consumer_key'])
    lti_user, created = LtiUser.objects.get_or_create(
        user_id=request.POST['user_id'],
        lti_consumer=lti_consumer,
    )
    log.debug("LTI user {}: user_id='{}'".format('created' if created else 'picked', lti_user.user_id))
    if not lti_user.is_askup_user:
        lti_user.lti_to_askup_user()
        log.debug('AskUp user was successfully created: {}'.format(lti_user.is_askup_user))
    lti_user.login(request)
    if not lti_user.is_registered_to_organization(qset.top_qset):
        lti_user.add_organization_to_lti_user(qset.top_qset)
    url = reverse('askup:qset', args=[qset.id])

    return redirect(url)
