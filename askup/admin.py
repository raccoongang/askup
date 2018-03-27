"""Admin views."""
from django.contrib import admin
from django.contrib.admin import StackedInline, TabularInline
from django.http import HttpResponseRedirect

from .forms import OrganizationModelForm, QuestionModelForm, UserForm
from .mixins.admin import CookieFilterMixIn
from .models import Domain, Organization, Profile, Qset, Question
from .utils.general import parse_response_url_to_parameters

from askup.models import User

class OrganizationFilter(admin.SimpleListFilter):
    """Provides an organization filter for the Qsets and Questions lists."""

    title = 'Organization'
    parameter_name = 'org'
    template = 'askup/filters/dropdown_filter.html'

    def lookups(self, request, model_admin):
        """Return a set of filter elements."""
        queryset = Qset.get_user_related_qsets_queryset(request.user)
        queryset = queryset.filter(parent_qset_id=None).order_by('name')
        items = [(org.id, org.name) for org in queryset]
        items.insert(0, ('0', 'All'))
        return items

    def queryset(self, request, queryset):
        """Return a queryset modified correspondingly to a filter."""
        if queryset.model is Question:
            return self.apply_question_queryset(queryset, request.user)
        elif queryset.model is Qset:
            return self.apply_qset_queryset(queryset, request.user)

        return queryset

    def apply_question_queryset(self, queryset, user):
        """Apply question queryset."""
        queryset = Question.apply_user_related_questions_filters(user, queryset)

        if self.value() == '0':
            return queryset

        if self.value():
            return queryset.filter(qset__top_qset_id=self.value())

    def apply_qset_queryset(self, queryset, user):
        """Apply qset queryset."""
        queryset = Qset.apply_user_related_qsets_filters(user, queryset)

        if self.value() == '0':
            return queryset

        if self.value():
            return queryset.filter(top_qset_id=self.value())


class QsetFilter(admin.SimpleListFilter):
    """Provides a qset filter for the Questions list."""

    title = 'Subject'
    parameter_name = 'qset'
    template = 'askup/filters/dropdown_filter.html'

    def lookups(self, request, model_admin):
        """Return a set of filter elements."""
        items = []
        org_id = request.GET.get('org', '0')
        queryset = Qset.objects.filter(parent_qset_id__gt=0)
        queryset = Qset.apply_user_related_qsets_filters(request.user, queryset)

        if org_id != '0':
            queryset = queryset.filter(top_qset_id=org_id)

        queryset = queryset.order_by('name')

        for qset in queryset:
            items.append((qset.id, qset.name))

        items.insert(0, ('0', 'All'))
        return items

    def queryset(self, request, queryset):
        """Return a queryset modified correspondingly to a filter."""
        queryset = Question.apply_user_related_questions_filters(request.user, queryset)

        if self.value() == '0':
            return queryset

        if self.value():
            return queryset.filter(qset_id=self.value())


class DomainsInline(TabularInline):
    model = Domain
    can_delete = True
    verbose_name_plural = 'Domains'
    fk_name = 'organization'
    extra = 0


class OrganizationAdmin(admin.ModelAdmin):
    """Admin view for the Organization model."""

    form = OrganizationModelForm
    list_display = ('name', 'domains')
    fields = (
        'name',
        'users',
    )
    inlines = (DomainsInline,)

    def get_inline_instances(self, request, obj=None):
        """
        Return an inline instances for the form.

        Overrides the function of the ModelForm with the same name.
        """
        if not obj:
            return list()

        return super().get_inline_instances(request, obj)

    @staticmethod
    def domains(obj):
        """Return email-patters of the organization comma separated."""
        return ", ".join(domain.name for domain in obj.domain_set.all())

    def get_queryset(self, request):
        """
        Get queryset for the list view.

        Overriding the queriset for the admin list view of the Organization
        """
        return super().get_queryset(request).order_by('name')


class QsetAdmin(CookieFilterMixIn, admin.ModelAdmin):
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
        form.base_fields['parent_qset'].initial = request.COOKIES.get('admin-filter-org')
        queryset = Qset.get_user_related_qsets_queryset(request.user).filter(parent_qset_id=None)
        form.base_fields['parent_qset'].queryset = queryset.order_by('name', 'parent_qset_id')
        return form

    def response_add(self, *args, **kwargs):
        """Set admin-filter-org cookie on qset creation."""
        response = super().response_add(*args, **kwargs)
        obj = args[1]

        if isinstance(response, HttpResponseRedirect):
            response = self.apply_organization_to_url(obj.parent_qset_id, response)

        response.set_cookie('admin-filter-org', obj.parent_qset_id)
        return response

    def response_change(self, *args, **kwargs):
        """Set admin-filter-org cookie on qset update."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]

        if isinstance(response, HttpResponseRedirect):
            response = self.apply_organization_to_url(obj.parent_qset_id, response)

        response.set_cookie('admin-filter-org', obj.parent_qset_id)
        return response

    def apply_organization_to_url(self, organization_id, response):
        """Apply organization filter value to the url on save."""
        url_path, parameters = parse_response_url_to_parameters(response)

        for i in range(len(parameters)):
            if parameters[i].startswith('org='):
                parameters[i] = 'org={0}'.format(organization_id)

        return HttpResponseRedirect('?'.join((url_path, ('&'.join(parameters)))))


class QuestionAdmin(CookieFilterMixIn, admin.ModelAdmin):
    """Admin list and detailed view for the Question model."""

    form = QuestionModelForm
    fields = (
        'text',
        'answer_text',
        'qset',
        'blooms_tag',
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
        queryset = Qset.apply_user_related_qsets_filters(request.user, queryset)
        queryset = queryset.order_by('name')
        form.base_fields['qset'].queryset = queryset
        form.current_user = request.user
        form.base_fields['qset'].initial = request.COOKIES.get('admin-filter-qset')
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
        response = super().response_add(*args, **kwargs)
        obj = args[1]

        if isinstance(response, HttpResponseRedirect):
            response = self.apply_org_and_qset_to_url(obj.qset_id, '0', response)

        response.set_cookie('admin-filter-qset', obj.qset_id)
        return response

    def response_change(self, *args, **kwargs):
        """Set admin-filter-qset cookie on question update."""
        response = super().response_change(*args, **kwargs)
        obj = args[1]

        if isinstance(response, HttpResponseRedirect):
            response = self.apply_org_and_qset_to_url(obj.qset_id, '0', response)

        response.set_cookie('admin-filter-qset', obj.qset_id)
        return response

    def apply_org_and_qset_to_url(self, qset_id, org_id, response):
        """Apply org and qset filter values to the url on save."""
        url_path, parameters = parse_response_url_to_parameters(response)
        parameters = self.update_parameters(parameters, qset_id, org_id)
        return HttpResponseRedirect('?'.join((url_path, ('&'.join(parameters)))))

    def update_parameters(self, parameters, qset_id, org_id):
        """Update parameters by filter values and return them."""
        filters = {'qset': str(qset_id), 'org': str(org_id)}
        filters = self.check_org_qset_relation(filters, 'org')

        for i in range(len(parameters)):
            if parameters[i].startswith('org='):
                parameters[i] = 'org={0}'.format(filters['org'])

            if parameters[i].startswith('qset='):
                parameters[i] = 'qset={0}'.format(filters['qset'])

        return parameters


class DomainAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Domain model."""

    fields = ('name', 'organization')
    list_display = ('name', 'organization')

    class Media:
        js = ('assets/hide_add_edit_icons.js',)


class UserProfileInline(StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

    def get_readonly_fields(self, request, obj=None):
        """
        Return a tuple of field names that should behave as a read only.
        """
        return ('email_confirmed',)


class UserAdmin(admin.ModelAdmin):
    """Admin list and detailed view for the Qset model."""

    form = UserForm
    list_display = ('username', 'email', 'first_name', 'last_name')
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        """
        Return an inline instances for the form.

        Overrides the function of the ModelForm with the same name.
        """
        if not obj:
            return list()

        return super().get_inline_instances(request, obj)


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Qset, QsetAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Domain, DomainAdmin)
#admin.site.unregister(User)
admin.site.register(User, UserAdmin)
