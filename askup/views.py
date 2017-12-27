"""Views of the Askup application"""

from django.views import generic

from .models import Qset, Question


class OrganizationsView(generic.ListView):
    """Handle the User Organizations list view"""
    template_name = 'askup/organizations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_title'] = 'Your organizations'
        return context

    def get_queryset(self):
        return Qset.objects.filter(parent_qset=None).order_by('name')


class OrganizationView(generic.ListView):
    """Beholds the Organization's root qsets list view"""
    template_name = 'askup/organization.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_title'] = Qset.objects.get(id=self.kwargs.get('pk')).name
        context['is_admin'] = self.request.user.is_superuser
        context['is_teacher'] = self.request.user.is_superuser
        return context

    def get_queryset(self):
        return Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))


class QsetView(generic.ListView):
    """Handles the Qset list view (subsets only/questions only/mixed)"""
    model = Qset

    def get_template_names(self):
        qset = Qset.objects.get(id=self.kwargs.get('pk'))

        if qset.type == 1:
            return ['askup/qset_subsets_only.html']
        elif qset.type == 2:
            return ['askup/qset_questions_only.html']
        else:
            return ['askup/qset_mixed.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions_list'] = Question.objects.filter(qset_id=self.kwargs.get('pk'))
        context['main_title'] = self._parent_qset.name
        context['is_qset_creator'] = self.request.user
        return context

    def get_queryset(self):
        queryset = Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))
        self._parent_qset = Qset.objects.filter(id=self.kwargs.get('pk'))[0]
        return queryset



class QuestionView(generic.DetailView):
    """Handles the Question detailed view"""
    model = Question
    template_name = 'askup/question.html'
