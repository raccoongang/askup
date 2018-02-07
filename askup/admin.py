"""Admin views."""
from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from .forms import UserForm, OrganizationModelForm
from .mixins.admin import CookieFilterMixIn, ParseUrlToParameters
from .models import EmailPattern, Organization, Qset, Question


class OrganizationFilter(admin.SimpleListFilter):
    """Provides an organization filter for the Qsets and Questions lists."""

    title = 'Organization'
    parameter_name = 'org'
    template = 'askup/filters/dropdown_filter.html'

    def lookups(self, request, model_admin):
        """Return a set of filter elements."""
        items = [(org.id, org.name) for org in Organization.objects.all().order_by('name')]
        items.insert(0, ('0', 'All'))
        return items

    def queryset(self, request, queryset):
        """Return a queryset modified correspondingly to a filter."""
        if queryset.model is Question:
            return self.apply_question_queryset(queryset)
        elif queryset.model is Qset:
            return self.apply_qset_queryset(queryset)

        return queryset

    def apply_question_queryset(self, queryset):
        """Apply question queryset."""
        if self.value():
            if self.value() == '0':
                return queryset
            else:
                return queryset.filter(qset__top_qset_id=self.value())

    def apply_qset_queryset(self, queryset):
        """Apply qset queryset."""
        if self.value():
            if self.value() == '0':
                return queryset
            else:
                return queryset.filter(top_qset_id=self.value())


class QsetFilter(admin.SimpleListFilter):
    """Provides a qset filter for the Questions list."""

    title = 'Qset'
    parameter_name = 'qset'
    template = 'askup/filters/dropdown_filter.html'

    def lookups(self, request, model_admin):
        """Return a set of filter elements."""
        items = []
        org_id = request.GET.get('org', '0')
        queryset = Qset.objects.filter(parent_qset_id__gt=0)

        if org_id != '0':
            queryset = queryset.filter(top_qset_id=org_id)

        queryset = queryset.order_by('name')

        for qset in queryset:
            items.append((qset.id, qset.name))

        items.insert(0, ('0', 'All'))
        return items

    def queryset(self, request, queryset):
        """Return a queryset modified correspondingly to a filter."""
        if self.value():
            if self.value() == '0':
                return queryset
            else:
                return queryset.filter(qset_id=self.value())


class OrganizationAdmin(admin.ModelAdmin):
    """Admin view for the Organization model."""

    form = OrganizationModelForm
    list_display = ('name', 'email_patterns')
    fields = (
        'name',
        'users',
    )

    @staticmethod
    def email_patterns(obj):
        """Return email-patters of the organization comma separated."""
        return ", ".join(tuple(pattern.text for pattern in obj.emailpattern_set.all()))

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Overriding the queriset for the admin list view of the Organization
        """
        return super().get_queryset(request).order_by('name')


class QsetAdmin(ParseUrlToParameters, CookieFilterMixIn, admin.ModelAdmin):
    """Admin list and detailed view for the Qset model."""

    fields = (
        'parent_qset',
        'name',
        'for_any_authenticated',
        'for_unauthenticated',
        'show_authors',
        'own_questions_only',
    )
    list_display = ('name', 'parent_qset', 'type')
    list_filter = (OrganizationFilter,)
    default_filters = {'org': '0'}
    cookie_filters = ('org',)

    class Media:
        js = ('assets/hide_add_edit_icons.js',)

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Override the queriset for the admin list view of the Qset.
        """
        return super().get_queryset(request).filter(parent_qset_id__gt=0).order_by(
            'parent_qset_id',
            'name',
        )

    def get_form(self, request, obj=None, **kwargs):
        """
        Get queryset for the list view.

        Overriding the form fields for the admin model form of the Qset.
        """
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['parent_qset'].label = 'Organization'
        form.base_fields['parent_qset'].required = True
        form.base_fields['parent_qset'].initial = request.COOKIES.get('admin-filter-org', None)
        queryset = Qset.objects.filter(parent_qset_id=None)

        if obj and obj.id:
            queryset = queryset.exclude(id=obj.id)

        form.base_fields['parent_qset'].queryset = queryset.order_by('name', 'parent_qset_id')
        return form

    def response_add(self, *args, **kwargs):
        """Set admin-filter-org cookie on qset creation."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]
        response = self.apply_organization_to_url(obj.parent_qset_id, response)
        response.set_cookie('admin-filter-org', obj.parent_qset_id)
        return response

    def response_change(self, *args, **kwargs):
        """Set admin-filter-org cookie on qset update."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]
        response = self.apply_organization_to_url(obj.parent_qset_id, response)
        response.set_cookie('admin-filter-org', obj.parent_qset_id)
        return response

    def apply_organization_to_url(self, organization_id, response):
        """Apply organization filter value to the url on save."""
        url_path, parameters = self.parse_response_url_to_parameters(response)

        for i in range(len(parameters)):
            if parameters[i][:4] == 'org=':
                parameters[i] = 'org={0}'.format(organization_id)

        return HttpResponseRedirect('?'.join((url_path, ('&'.join(parameters)))))


class QuestionAdmin(ParseUrlToParameters, CookieFilterMixIn, admin.ModelAdmin):
    """Admin list and detailed view for the Question model."""

    fields = (
        'text',
        'answer_text',
        'qset',
        'blooms_tag',
        'vote_value',
    )
    list_display = ('text', 'qset')
    list_filter = (OrganizationFilter, QsetFilter)
    default_filters = {'org': '0', 'qset': '0'}
    cookie_filters = ('org', 'qset')

    def get_form(self, request, obj=None, **kwargs):
        """
        Get queryset for the list view.

        Overriding the form fields for the admin model form of the Questions.
        """
        form = super().get_form(request, obj, **kwargs)
        queryset = Qset.objects.filter(
            parent_qset_id__isnull=False, type__in=(0, 2)
        )
        queryset = queryset.order_by('name')
        form.base_fields['qset'].queryset = queryset
        form.base_fields['qset'].initial = request.COOKIES.get('admin-filter-qset', None)
        return form

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Override the queriset for the admin list view of the Questions.
        """
        queryset = super().get_queryset(request)
        return queryset.order_by('text', 'qset')

    def get_readonly_fields(self, request, obj=None):
        """Return a tuple of field names that should behave as a read only."""
        return ('vote_value',)

    def save_model(self, *args, **kwargs):
        """Apply user id to the question when created through the admin panel."""
        args[1].user_id = args[0].user.id
        super().save_model(*args, **kwargs)

    def response_add(self, *args, **kwargs):
        """Set admin-filter-qset on question creation."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]
        response = self.apply_org_and_qset_to_url(obj.qset_id, obj.qset.top_qset_id, response)
        response.set_cookie('admin-filter-qset', obj.qset_id)
        return response

    def response_change(self, *args, **kwargs):
        """Set admin-filter-qset cookie on question update."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]
        response = self.apply_org_and_qset_to_url(obj.qset_id, obj.qset.top_qset_id, response)
        response.set_cookie('admin-filter-qset', obj.qset_id)
        return response

    def apply_org_and_qset_to_url(self, qset_id, org_id, response):
        """Apply org and qset filter values to the url on save."""
        url_path, parameters = self.parse_response_url_to_parameters(response)
        filters = {'qset': str(qset_id), 'org': str(org_id)}
        filters = self.check_org_qset_relation(filters, 'org')

        for i in range(len(parameters)):
            if parameters[i][:5] == 'qset=':
                parameters[i] = 'qset={0}'.format(filters['qset'])

            if parameters[i][:4] == 'org=':
                parameters[i] = 'org={0}'.format(filters['org'])

        return HttpResponseRedirect('?'.join((url_path, ('&'.join(parameters)))))


class EmailPatternAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the EmailPattern model."""

    fields = ('organization', 'text')
    list_display = ('organization', 'text')


class UserAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Qset model."""

    form = UserForm
    list_display = ('username', 'email', 'first_name', 'last_name')


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Qset, QsetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(EmailPattern, EmailPatternAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
