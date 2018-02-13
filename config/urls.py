"""config URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))

"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from askup.views import index_view

urlpatterns = [
    url(r'^$', index_view, name='index'),
    url(r'^admin/', admin.site.urls),
    url(
        r'^password-reset$',
        auth_views.password_reset,
        {'template_name': 'askup/password_reset_form.html'},
        name='password_reset',
    ),
    url(
        r'^password-reset-done$',
        auth_views.password_reset_done,
        {'template_name': 'askup/password_reset_done.html'},
        name='password_reset_done',
    ),
    url(
        r'^password-reset-confirm/(?P<uidb64>[^/]+)/(?P<token>[^/]+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'askup/password_reset_confirm.html'},
        name='password_reset_confirm',
    ),
    url(
        r'^password-reset-complete$',
        auth_views.password_reset_complete,
        {'template_name': 'askup/password_reset_complete.html'},
        name='password_reset_complete',
    ),
    url(r'^askup/', include('askup.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
