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
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from askup import views

app_name = 'askup'

STATIC_URL = '/assets/'

urlpatterns = [
    url(r'^$', views.OrganizationsView.as_view(), name='organizations'),
    url(r'^admin/', admin.site.urls),
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, name='logout'),
    url(r'^org/(?P<pk>[0-9]+)/$', views.OrganizationView.as_view(), name='organization'),
    url(r'^organizations$', views.OrganizationsView.as_view(), name='organizations'),
    url(r'^qset/(?P<pk>[0-9]+)/$', views.QsetView.as_view(), name='qset'),
    url(r'^question/(?P<pk>[0-9]+)/$', views.QuestionView.as_view(), name='question'),
] + static(
    '/assets/',
    document_root='/home/khaimovmr/git/rg-askup-django/askup/assets/'
)
