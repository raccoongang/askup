"""Url configuration for the askup application."""

from django.conf.urls import url

from . import views

app_name = 'askup'

urlpatterns = [
    url(
        r'^sign-up-activation-sent/$',
        views.sign_up_activation_sent,
        name='sign_up_activation_sent'
    ),
    url(
        r'^sign-up-activate/(?P<uid>\d+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.sign_up_activate,
        name='sign_up_activate'
    ),
    url(r'^sign-up$', views.sign_up_view, name='sign_up'),
    url(r'^sign-in$', views.login_view, name='sign_in'),
    url(r'^sign-out$', views.logout_view, name='sign_out'),
    url(r'^organization/(?P<pk>\d+)/$', views.OrganizationView.as_view(), name='organization'),
    url(r'^public-qsets/$', views.public_qsets_view, name='public_qsets'),
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
    url(r'^question/new/(?P<qset_id>\d+)/$', views.question_create, name='qset_question_create'),
    url(r'^question/new/$', views.question_create, name='question_create'),
    url(r'^question/edit/(?P<pk>\d+)/$', views.question_edit, name='question_edit'),
    url(r'^question/delete/(?P<pk>\d+)/$', views.question_delete, name='question_delete'),
    url(
        r'^question/upvote/(?P<question_id>\d+)/$',
        views.question_upvote,
        name='question_upvote'
    ),
    url(
        r'^question/downvote/(?P<question_id>\d+)/$',
        views.question_downvote,
        name='question_downvote'
    ),
    url(
        r'^answer/evaluate/(?P<answer_id>\d+)/(?P<evaluation>\d+)/$',
        views.answer_evaluate,
        name='answer_evaluate'
    ),
    url(r'^user/profile/(?P<user_id>\d+)/$', views.user_profile_view, name='user_profile'),
    url(r'^user/profile/rank-list/(?P<user_id>\d+)/$', views.user_profile_rank_list_view, name='user_profile_rank_list'),
    url(r'^feedback/$', views.feedback_form_view, name='feedback'),
]
