import logging

from crispy_forms.bootstrap import InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Fieldset, HTML, Layout, Submit
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.db import models
from django.urls import reverse

from askup.mixins.forms import InitFormWithCancelButtonMixIn, UsernameCleanMixIn
from askup.models import Organization, Qset, Question


log = logging.getLogger(__name__)


class SignUpForm(UsernameCleanMixIn, InitFormWithCancelButtonMixIn, UserCreationForm):
    """
    Form for the User Sign Up process.
    """

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all().order_by('name'),
        empty_label='apply to organization...',
        required=False,
        help_text='',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def _set_up_fields(self, *args, **kwargs):
        """
        Set up custom fields behaviour.
        """
        queryset = self.fields['organization'].queryset.select_related().annotate(
            email_restricted=models.Sum('domain__id')
        )
        self.fields['email'].required = True
        self.fields['username'].help_text = ''
        self.fields['organization'].required = True
        self.fields['organization'].queryset = queryset
        self.fields['organization'].choices = self.compose_organization_choices(queryset)
        help_text = (
            'Organization you will be applied to, after the registration<br/>' +
            '<a href="{}?next={}&subject={}">I want to become a teacher</a>'
        )
        self.fields['organization'].help_text = help_text.format(
            reverse('askup:feedback'),
            reverse('askup:sign_up'),
            'I want to become a teacher...'
        )

    def compose_organization_choices(self, queryset):
        """
        Return a customized organization choices.
        """
        choices = [('', 'select an organization to apply...')]

        for organization in queryset:
            template = '{} [email restricted]' if organization.email_restricted else '{}'
            choices.append((organization.id, template.format(organization.name)))

        return choices

    def _set_up_helper(self, qset_id):
        """
        Set up form helper that describes the form html structure.
        """
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-4 col-md-4 col-lg-4'
        self.helper.field_class = 'col-xs-8 col-md-6 col-lg-8'
        self.helper.layout = Layout(
            'username',
            'email',
            'first_name',
            'last_name',
            'password1',
            'password2',
            'organization',
            ButtonHolder(
                HTML(
                    '<a class="btn btn-flat cancel-btn" href="{}">Cancel</a>'.format(
                        reverse('askup:sign_in')
                    )
                ),
                Submit('submit', 'Sign Up', css_class='btn btn-theme'),
                css_class='center',
            )
        )

    def clean_organization(self, *args, **kwargs):
        """
        Validate the organization field.
        """
        organization = self.cleaned_data['organization']
        email = self.cleaned_data.get('email')

        if not self.check_if_organization_is_permitted(organization, email):
            raise forms.ValidationError(
                "This organization is an email restricted. " +
                "You should specify an email from one of it's domains."
            )
        return self.cleaned_data['organization']

    def check_if_organization_is_permitted(self, organization, user_email):
        """
        Check whether this organization is permitted for the email specified.

        Return True if organization isn't selected or domain of user email is in
        the organization domains (can be added/modified in the admin panel).
        """
        if not organization or not organization.domain_set.exists():
            return True

        for domain in organization.domain_set.all():
            if user_email.endswith('@{}'.format(domain.name)):
                return True

        return False


class UserLoginForm(UsernameCleanMixIn, forms.Form):
    """Handles the user login form behaviour."""

    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Your username or email...'
        self.fields['password'].widget.attrs['placeholder'] = 'Your password...'

    def clean(self, *args, **kwargs):
        """
        Validate the login form fields.

        Overriding the same method of the forms.Form
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)

        if not user:
            email_user = User.objects.filter(email=username).first()
            user = email_user and authenticate(username=email_user.username, password=password)

        if not user:
            raise forms.ValidationError("This user doesn't exist")

        if not user.is_active:
            raise forms.ValidationError("This user is no longer active")

        login(self._request, user)
        return super().clean(*args, **kwargs)


class UserForm(UsernameCleanMixIn, forms.ModelForm):
    """Handles the user create/edit form behaviour."""

    password = forms.CharField(widget=forms.PasswordInput)
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        widget=forms.Select,
    )
    organizations = forms.ModelMultipleChoiceField(
        queryset=Qset.objects.filter(parent_qset_id__isnull=True).order_by('name'),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Organizations',
            is_stacked=False
        )
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'is_active',
            'groups',
            'organizations',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].required = True
        self.fields['username'].help_text = ''
        self.fields['email'].required = True
        self.fields['password'].required = self.instance.id is None  # Required on user creation

        if self.instance.id:
            group = self.instance.groups.all().first()
            self.initial['groups'] = group.id if group else None

        self.fields['groups'].empty_label = 'select a role...'
        self.fields['groups'].label = 'Role'
        self.fields['groups'].required = True
        self.fields['groups'].error_messages['required'] = "At least one group should be selected."

        if self.instance.id:
            self.fields['organizations'].initial = self.instance.qset_set.all()

    def clean_email(self):
        """Check email for non matching with other user's username."""
        user = self.instance
        queryset = User.objects.filter(username=self.cleaned_data['email']).exclude(id=user.id)

        if user and queryset.first():
            raise forms.ValidationError("This username or email is already exists.")

        return self.cleaned_data['email']

    def clean_password(self, *args, **kwargs):
        """Clean the password field data received."""
        if self.instance.id and not self.cleaned_data['password']:
            return self.instance.password

        return make_password(self.cleaned_data['password'])

    def clean_groups(self, *args, **kwargs):
        """
        Process Groups field changes.

        Set is_staff to users, who have an 'admin' or a 'teacher' groups.
        Overriding the Form.clean_<field_name> method.
        """
        new_group = str(self.cleaned_data['groups']).lower()
        has_staff_groups = new_group in ('admin', 'teacher')

        if has_staff_groups and self.instance.is_staff is False:
            self.instance.is_staff = True
        elif not has_staff_groups and self.instance.is_staff is True:
            self.instance.is_staff = False

        return [self.cleaned_data['groups']]

    def save(self, commit=True):
        """Save the Organization fields to the user related model."""
        user = super().save(commit=False)
        user.save()
        user.qset_set = self.cleaned_data['organizations']
        return user


class OrganizationModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Organization."""

    class Meta:
        model = Organization
        fields = (
            'name',
        )
        widgets = {
            'users': FilteredSelectMultiple(verbose_name='Users', is_stacked=False),
            'domains': FilteredSelectMultiple(verbose_name='Domains', is_stacked=False),
        }


class QsetModelForm(InitFormWithCancelButtonMixIn, forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def _set_up_fields(self, user):
        """Set up additional fields rules."""
        self.fields['parent_qset'].required = True
        self.fields['parent_qset'].empty_label = None
        queryset = Qset.get_user_related_qsets(
            user,
            ('top_qset_id', '-is_organization', 'askup_qset.name'),
            organizations_only=True,
        )
        queryset = queryset.filter(parent_qset__isnull=True)
        self.fields['parent_qset'].queryset = queryset
        self.fields['for_any_authenticated'].label = 'Questions are visible to all logged-in users'
        self.fields['for_unauthenticated'].label = 'Questions are visible to unauthenticated users'
        self.fields['show_authors'].label = 'Questions authors are visible to all users'

    def _set_up_helper(self, qset_id):
        """Set up form helper that describes the form html structure."""
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                Div('name', css_class='row center'),
                Div('parent_qset', css_class='row center'),
                self._get_checkbox_row('for_any_authenticated'),
                self._get_checkbox_row('for_unauthenticated'),
                self._get_checkbox_row('show_authors'),
            ),
            self._get_helper_buttons(qset_id)
        )

    def _get_checkbox_row(self, field_name):
        return Div(
            Div(css_class="col-xs-1"),
            Div(field_name, css_class='col-xs-10'),
            Div(css_class="col-xs-1"),
            css_class="col-xs-12 row",
        )

    class Meta:
        model = Qset
        fields = (
            'name',
            'parent_qset',
            'for_any_authenticated',
            'show_authors',
            'for_unauthenticated',
        )


class QsetDeleteModelForm(forms.ModelForm):
    """Provides the delete functionality for the Qset."""

    class Meta:
        model = Qset
        fields = []


class QuestionModelForm(InitFormWithCancelButtonMixIn, forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    class Meta:
        model = Question
        fields = (
            'qset',
            'text',
            'answer_text',
            'blooms_tag',
        )
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Type a question here...'}),
            'answer_text': forms.Textarea(attrs={'placeholder': 'Type an answer here...'}),
        }

    def _set_up_fields(self, user):
        self.fields['qset'].required = True
        self.fields['qset'].empty_label = None
        self.fields['qset'].queryset = Qset.get_user_related_qsets(
            user,
            ('top_qset__name', '-is_organization', 'askup_qset.name'),
            qsets_only=True,
        )
        self.fields['text'].placeholder = 'Question'
        self.fields['text'].label = 'Question'
        self.fields['answer_text'].placeholder = 'Answer'
        self.fields['answer_text'].label = 'Answer'
        self.fields['blooms_tag'].choices[0] = ("", "- no tag -")
        self.fields['blooms_tag'].label = 'Bloom\'s category'
        self.fields['qset'].label = 'Subject'
        self.fields['qset'].choices = self.get_qset_choices(self.fields['qset'].queryset)

    def get_qset_choices(self, qsets):
        """
        Get choices for the qset field.
        """
        choices = [('', 'select a subject...')]

        for qset in qsets:
            choices.append(
                (
                    qset.id,
                    '{0}: {1}'.format(qset.top_qset.name, qset.name)
                )
            )

        return choices

    def _set_up_helper(self, qset_id):
        """Set up form helper that describes the form html structure."""
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                Div(
                    Div('text', css_class='col-sm-12'),
                    css_class='row'
                ),
                Div(
                    Div('answer_text', css_class='col-sm-12'),
                    css_class='row'
                ),
                InlineRadios(
                    'blooms_tag',
                    template='askup/layout/radioselect_inline.html',
                    hide='true'
                ),
                Div('qset'),
            ),
            self._get_helper_buttons(qset_id, 'Create' if self.instance.id is None else 'Save')
        )


class QuestionDeleteModelForm(InitFormWithCancelButtonMixIn, forms.ModelForm):
    """Provides the delete functionality for the Question."""

    def __init__(self, *args, **kwargs):
        """
        Init the QuestionDeleteModelForm.

        Overriding the same method of the forms.ModelForm
        """
        qset_id = kwargs.pop('parent_qset_id', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            self._get_helper_buttons(qset_id, 'Delete')
        )

    class Meta:
        model = Question
        fields = []


class AnswerModelForm(InitFormWithCancelButtonMixIn, forms.ModelForm):
    """Provides the create/update functionality for the Answer."""

    def __init__(self, *args, **kwargs):
        """
        Init the AnswerModelForm.

        Overriding the same method of the forms.ModelForm
        """
        is_quiz_all = kwargs.get('is_quiz_all')
        qset_id = kwargs.pop('parent_qset_id', None)
        super().__init__(*args, **kwargs)
        self.fields['text'].required = True
        self.fields['text'].label = 'Answer'
        self.fields['text'].error_messages['required'] = 'Please answer the question'
        self.helper = FormHelper()

        if is_quiz_all:
            self.helper.form_action = "?is_quiz_all=1"

        self.helper.layout = Layout(
            Fieldset(
                '',
                Div('text', custom_valid_message="Please answer the question"),
            ),
            self._get_helper_buttons(qset_id, 'Submit')
        )

    class Meta:
        model = Question
        fields = [
            'text',
        ]
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'placeholder': 'Type your answer here...',
                    'rows': 2,
                }
            ),
        }


class FeedbackForm(InitFormWithCancelButtonMixIn, forms.Form):
    """Provides the create/update functionality for the Qset."""

    email = forms.EmailField()
    subject = forms.CharField(min_length=3, max_length=60)
    message = forms.CharField(min_length=10, max_length=2000, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop('subject', None)
        super().__init__(*args, **kwargs)
        user = kwargs.pop('user', None)
        self.fields['email'].widget.attrs['placeholder'] = 'Your email...'

        if user and user.id:
            self.fields['email'].initial = user.email
            self.fields['email'].widget.attrs['readonly'] = True

        if subject:
            self.fields['subject'].initial = subject

        self.fields['subject'].widget.attrs['placeholder'] = 'Feadback subject...'
        self.fields['message'].widget.attrs['placeholder'] = 'Feadback message...'

    def _set_up_helper(self, qset_id):
        """Set up form helper that describes the form html structure."""
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                Div(
                    Div('email', css_class='col-sm-12'),
                    css_class='row'
                ),
                Div(
                    Div('subject', css_class='col-sm-12'),
                    css_class='row'
                ),
                Div(
                    Div('message', css_class='col-sm-12'),
                    css_class='row'
                ),
            ),
            self._get_helper_buttons(None, submit_name='Send')
        )

    def _get_cancel_button(self, qset_id):
        """Return cancel button element of the form layout."""
        return HTML(
            '<a class="btn btn-flat cancel-btn" href="/">' +
            'Cancel' +
            '</a>'
        )
