"""Url configuration for the askup application."""

from django.conf.urls import url

from . import views

app_name = 'askup'

urlpatterns = [
    url(r'^sign-in$', views.login_view, name='sign_in'),
    url(r'^sign-out$', views.logout_view, name='sign_out'),
    url(r'^organization/(?P<pk>[0-9]+)/$', views.OrganizationView.as_view(), name='organization'),
    url(r'^organizations$', views.OrganizationsView.as_view(), name='organizations'),
    url(r'^qset/(?P<pk>[0-9]+)/$', views.QsetView.as_view(), name='qset'),
    url(r'^qset/new/$', views.create_qset, name='qset_create'),
    url(r'^question/(?P<pk>[0-9]+)/$', views.QuestionView.as_view(), name='question'),
    url(r'^question/new/(?P<qset_id>[^/]+)/$', views.create_question, name='question_create'),
]
