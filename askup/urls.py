"""Url configuration for the askup application."""

from django.conf.urls import url

from . import views

app_name = 'askup'

urlpatterns = [
    url(r'^org/(?P<pk>[0-9]+)/$', views.OrganizationView.as_view(), name='organization'),
    url(r'^organizations$', views.OrganizationsView.as_view(), name='organizations'),
    url(r'^qset/(?P<pk>[0-9]+)/$', views.QsetView.as_view(), name='qset'),
    url(r'^question/(?P<pk>[0-9]+)/$', views.QuestionView.as_view(), name='question'),
]
