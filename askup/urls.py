"""Url configuration for the askup application."""

from django.conf.urls import url

from . import views

app_name = 'askup'

urlpatterns = [
    url(r'^sign-in$', views.login_view, name='sign_in'),
    url(r'^sign-out$', views.logout_view, name='sign_out'),
    url(r'^organization/(?P<pk>\d+)/$', views.OrganizationView.as_view(), name='organization'),
    url(r'^organizations$', views.OrganizationsView.as_view(), name='organizations'),
    url(
        r'^organization/update/(?P<pk>\d+)/$',
        views.organization_update,
        name='organization_update'
    ),
    url(r'^qset/(?P<pk>\d+)/$', views.QsetView.as_view(), name='qset'),
    url(r'^qset/new/$', views.qset_create, name='qset_create'),
    url(r'^qset/update/(?P<pk>\d+)/$', views.qset_update, name='qset_update'),
    url(r'^qset/delete/(?P<pk>\d+)/$', views.qset_delete, name='qset_delete'),
    url(r'^qset/quiz/all/(?P<qset_id>\d+)/$', views.start_quiz_all, name='start_quiz_all'),
    url(r'^question/answer/(?P<question_id>\d+)/$', views.question_answer, name='question_answer'),
    url(r'^question/(?P<pk>\d+)/$', views.QuestionView.as_view(), name='question'),
    url(r'^question/new/(?P<qset_id>\d+)/$', views.question_create, name='qset_question_create'),
    url(r'^question/new/$', views.question_create, name='question_create'),
    url(r'^question/edit/(?P<pk>\d+)/$', views.question_edit, name='question_edit'),
    url(r'^question/delete/(?P<pk>\d+)/$', views.question_delete, name='question_delete'),
    url(
        r'^question/upvote/(?P<question_id>\d+)/$',
        views.question_upvote, name='question_vote_up'
    ),
    url(
        r'^question/downvote/(?P<question_id>\d+)/$',
        views.question_downvote,
        name='question_vote_down'
    ),
    url(
        r'^answer/evaluate/(?P<answer_id>\d+)/(?P<evaluation>\d+)/$',
        views.answer_evaluate,
        name='answer_evaluate'
    ),
    url(r'^user_profile/$', views.UserProfileView.as_view(), name='user_profile'),
]
