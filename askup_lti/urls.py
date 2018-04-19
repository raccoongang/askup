from django.conf.urls import url

from .provider import lti_launch

urlpatterns = [
    url(r'^launch/?(?:/qset/(?P<qset_id>\d+)/?)?$', lti_launch, name='launch'),
]
