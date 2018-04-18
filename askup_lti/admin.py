from django.contrib import admin

from .models import LtiProvider, LtiUser


admin.site.register(LtiProvider)
admin.site.register(LtiUser)
