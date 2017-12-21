#from django.shortcuts import render
import logging
from django.views import generic
from .models import Qset, Question, Answer, User

from django.contrib.auth.models import User as U


logging.root.setLevel(logging.DEBUG)


class OrganizationsView(generic.ListView):
    template_name = 'askup/organizations.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationsView, self).get_context_data(**kwargs)
        context['main_title'] = 'Your organizations'
        return context

    def get_queryset(self):
        if self.request.user.is_superuser:
            logging.debug('IS ADMIN CHECK: this user is admin')
        else:
            logging.debug('IS ADMIN CHECK: this user is not admin')
        return Qset.objects.filter(parent_qset=None).order_by('name')


class OrganizationView(generic.ListView):
    template_name = 'askup/organization.html'

    def get_context_data(self, **kwargs):
        context = super(OrganizationView, self).get_context_data(**kwargs)
        context['main_title'] = Qset.objects.get(id=self.kwargs.get('pk')).name
        return context

    def get_queryset(self):
        return Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))


class QsetView(generic.ListView):
    model = Qset
    #template_name = 'askup/qset.html'

    def get_template_names(self):
        qset = Qset.objects.get(id=self.kwargs.get('pk'))
        logging.debug("QSET TYPE: {0}".format(qset.type))

        if qset.type == 1:
            return ['askup/qset_subsets_only.html']
        elif qset.type == 2:
            return ['askup/qset_questions_only.html']
        else:
            return ['askup/qset_mixed.html']

    def get_context_data(self, **kwargs):
        context = super(QsetView, self).get_context_data(**kwargs)
        context['questions_list'] = Question.objects.filter(qset_id=self.kwargs.get('pk'))
        context['main_title'] = self._parent_qset.name
        context['fluid'] = '-fluid'
        context['is_qset_creator'] = self.request.user
        return context

    def get_queryset(self):
        queryset = Qset.objects.filter(parent_qset_id=self.kwargs.get('pk'))
        self._parent_qset = Qset.objects.filter(id=self.kwargs.get('pk'))[0]
        return queryset



class QuestionView(generic.ListView):
    model = Question
    template_name = 'askup/question.html'

