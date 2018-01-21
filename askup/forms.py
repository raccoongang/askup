import logging

from crispy_forms.bootstrap import InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Fieldset, HTML, Layout, Submit
from django import forms
from django.contrib.auth import authenticate
from django.urls import reverse

from .models import Organization, Qset, Question


log = logging.getLogger(__name__)


class UserLoginForm(forms.Form):
    """Handles the user login form behaviour."""

    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

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


class OrganizationModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Organization."""

    def __init__(self, *args, **kwargs):
        """
        Init the OrganizationModelForm.

        Overriding the same method of the forms.ModelForm
        """
        super().__init__(*args, **kwargs)

    class Meta:
        model = Organization
        fields = (
            'name',
        )


class QsetModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def __init__(self, *args, **kwargs):
        """
        Init the QsetModelForm.

        Overriding the same method of the forms.ModelForm
        """
        qset_id = kwargs.pop('parent_qset_id', None)
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        if qset_id:
            cancel_url = reverse('askup:qset', kwargs={'pk': qset_id})
        else:
            cancel_url = reverse('askup:organizations')

        self.fields['parent_qset'].required = True
        self.fields['parent_qset'].empty_label = None
        self.fields['parent_qset'].queryset = Qset.get_user_related_qsets(
            user,
            ('top_qset_id', '-is_organization', 'askup_qset.name')
        )
        self.fields['for_any_authenticated'].label = 'Questions are visible to all logged-in users'
        self.fields['for_unauthenticated'].label = 'Questions are visible to unauthenticated users'
        self.fields['show_authors'].label = 'Questions authors are visible to all users'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                Div('name', css_class='row center'),
                Div('parent_qset', css_class='row center'),
                Div(
                    Div(css_class="col-xs-1"),
                    Div('for_any_authenticated', css_class='col-xs-10'),
                    Div(css_class="col-xs-1"),
                    css_class="col-xs-12 row",
                ),
                Div(
                    Div(css_class="col-xs-1"),
                    Div('for_unauthenticated', css_class='col-xs-10'),
                    Div(css_class="col-xs-1"),
                    css_class="col-xs-12 row",
                ),
                Div(
                    Div(css_class="col-xs-1"),
                    Div('show_authors', css_class='col-xs-10'),
                    Div(css_class="col-xs-1"),
                    css_class="col-xs-12 row",
                ),
                Div(
                    InlineRadios('type', template='askup/layout/radioselect_inline.html'),
                    css_class='row center'
                ),
            ),
            ButtonHolder(
                HTML(
                    '<a class="btn btn-flat cancel-btn" href="{0}">'.format(cancel_url) +
                    'Cancel' +
                    '</a>'
                ),
                Submit('submit', 'Save', css_class='btn btn-theme'),
                css_class="center",
            )
        )

    class Meta:
        model = Qset
        fields = (
            'name',
            'parent_qset',
            'type',
            'for_any_authenticated',
            'show_authors',
            'for_unauthenticated',
        )


class QsetDeleteModelForm(forms.ModelForm):
    """Provides the delete functionality for the Qset."""

    class Meta:
        model = Qset
        fields = []


class QuestionModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Qset."""

    def __init__(self, *args, **kwargs):
        """
        Init the QuestionModelForm.

        Overriding the same method of the forms.ModelForm
        """
        qset_id = kwargs.pop('parent_qset_id', None)
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

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
        self.helper = FormHelper()

        if qset_id:
            cancel_url = reverse('askup:qset', kwargs={'pk': qset_id})
        else:
            cancel_url = reverse('askup:organizations')

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
            ButtonHolder(
                HTML(
                    '<a class="btn btn-flat cancel-btn" href="{0}">'.format(cancel_url) +
                    'Cancel' +
                    '</a>'
                ),
                Submit('submit', 'Save', css_class='btn btn-theme'),
            )
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


class QuestionDeleteModelForm(forms.ModelForm):
    """Provides the delete functionality for the Question."""

    def __init__(self, *args, **kwargs):
        """
        Init the QuestionDeleteModelForm.

        Overriding the same method of the forms.ModelForm
        """
        qset_id = kwargs.pop('parent_qset_id', None)
        super().__init__(*args, **kwargs)

        if qset_id:
            cancel_url = reverse('askup:qset', kwargs={'pk': qset_id})
        else:
            cancel_url = reverse('askup:organizations')

        self.helper = FormHelper()
        self.helper.layout = Layout(
            ButtonHolder(
                HTML(
                    '<a class="btn btn-flat cancel-btn" href="{0}">'.format(cancel_url) +
                    'Cancel' +
                    '</a>'
                ),
                Submit('submit', 'Delete', css_class='btn btn-pink'),
            )
        )

    class Meta:
        model = Question
        fields = []


class AnswerModelForm(forms.ModelForm):
    """Provides the create/update functionality for the Answer."""

    def __init__(self, *args, **kwargs):
        """
        Init the AnswerModelForm.

        Overriding the same method of the forms.ModelForm
        """
        qset_id = kwargs.pop('parent_qset_id', None)

        super().__init__(*args, **kwargs)

        self.fields['text'].required = True

        if qset_id:
            cancel_url = reverse('askup:qset', kwargs={'pk': qset_id})
        else:
            cancel_url = reverse('askup:organizations')

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                Div('text'),
            ),
            ButtonHolder(
                HTML(
                    '<a class="btn btn-flat cancel-btn" href="{0}">'.format(cancel_url) +
                    'Cancel' +
                    '</a>'
                ),
                Submit('submit', 'Submit', css_class='btn btn-theme submit-answer'),
            )
        )

    class Meta:
        model = Question
        fields = [
            'text',
        ]
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'placeholder': 'Type your answer here...'
                }
            ),
        }
