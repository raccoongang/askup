import logging

from crispy_forms.bootstrap import InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Fieldset, Layout
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from .mixins.forms import InitFormWithCancelButtonMixin
from .models import Organization, Qset, Question


log = logging.getLogger(__name__)


class UserLoginForm(forms.Form):
    """Handles the user login form behaviour."""

    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = ''
        self.fields['username'].widget.attrs['placeholder'] = 'Your username or email...'
        self.fields['password'].label = ''
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
            raise forms.ValidationError("This user doesn't exist")

        if not user.check_password(password):
            raise forms.ValidationError("Incorrect password")

        if not user.is_active:
            raise forms.ValidationError("This user is no longer active")

        return super().clean(*args, **kwargs)


class UserForm(forms.ModelForm):
    """Handles the user create/edit form behaviour."""

    password = forms.CharField(widget=forms.PasswordInput)

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
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].required = True
        self.fields['email'].required = True
        self.fields['password'].required = self.instance.id is None  # Required on user creation
        self.fields['groups'].required = True
        self.fields['groups'].error_messages['required'] = "At least one group should be selected."

    def clean_username(self):
        """Check username for non matching with other user's email."""
        user = self.instance
        queryset = User.objects.filter(email=self.cleaned_data['username']).exclude(id=user.id)

        if user and queryset.first():
            raise forms.ValidationError("This username or email is already exists.")

        return self.cleaned_data['username']

    def clean_email(self):
        """Check email for non matching with other user's username."""
        user = self.instance
        queryset = User.objects.filter(username=self.cleaned_data['email']).exclude(id=user.id)

        if user and queryset.first():
            raise forms.ValidationError("This username or email is already exists.")

        return self.cleaned_data['email']

    def clean_password(self, *args, **kwargs):
        if self.instance.id and not self.cleaned_data['password']:
            return self.instance.password

        return make_password(self.cleaned_data['password'])

    def clean_groups(self, *args, **kwargs):
        """
        Process Groups field changes.

        Set is_staff to users, who have an 'admins' or a 'teachers' groups.
        Overriding the Form.clean_<field_name> method.
        """
        new_groups = set(str(group).lower() for group in self.cleaned_data['groups'])
        has_staff_groups = new_groups.intersection(('admins', 'teachers'))

        if has_staff_groups and self.instance.is_staff is False:
            self.instance.is_staff = True
        elif not has_staff_groups and self.instance.is_staff is True:
            self.instance.is_staff = False

        return self.cleaned_data['groups']


class OrganizationModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Organization."""

    class Meta:
        model = Organization
        fields = (
            'name',
        )


class QsetModelForm(InitFormWithCancelButtonMixin, forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def _set_up_fields(self, user):
        """Set up additional fields rules."""
        self.fields['parent_qset'].required = True
        self.fields['parent_qset'].empty_label = None
        self.fields['parent_qset'].queryset = Qset.get_user_related_qsets(
            user,
            ('top_qset_id', '-is_organization', 'askup_qset.name')
        )
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


class QuestionModelForm(InitFormWithCancelButtonMixin, forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def _set_up_fields(self, user):
        self.fields['qset'].required = True
        self.fields['qset'].empty_label = None
        self.fields['qset'].queryset = Qset.get_user_related_qsets(
            user,
            ('top_qset_id', '-is_organization', 'askup_qset.name'),
            qsets_only=True
        )
        self.fields['text'].placeholder = 'Question'
        self.fields['text'].label = ''
        self.fields['answer_text'].placeholder = 'Answer'
        self.fields['answer_text'].label = ''
        self.fields['blooms_tag'].choices[0] = ("", "- no tag -")

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
            self._get_helper_buttons(qset_id)
        )

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


class QuestionDeleteModelForm(InitFormWithCancelButtonMixin, forms.ModelForm):
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


class AnswerModelForm(InitFormWithCancelButtonMixin, forms.ModelForm):
    """Provides the create/update functionality for the Answer."""

    def __init__(self, *args, **kwargs):
        """
        Init the AnswerModelForm.

        Overriding the same method of the forms.ModelForm
        """
        is_quiz_all = kwargs.get('is_quiz_all', None)
        qset_id = kwargs.pop('parent_qset_id', None)
        super().__init__(*args, **kwargs)
        self.fields['text'].required = True
        self.helper = FormHelper()

        if is_quiz_all:
            self.helper.form_action = "?is_quiz_all=1"

        self.helper.layout = Layout(
            Fieldset(
                '',
                Div('text'),
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
