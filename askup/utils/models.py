from django.shortcuts import redirect
from django.urls import reverse

from askup.models import Question
from .general import check_user_has_groups


def check_user_and_create_question(user, qset, text, answer_text, blooms_tag):
    """Check user permissions and create question in the database."""
    if not check_user_has_groups(user, 'admin') and user not in qset.top_qset.users.all():
        return None, redirect(reverse('askup:organizations'))

    Question.objects.create(
        text=text,
        answer_text=answer_text,
        qset_id=qset.id,
        user_id=user.id,
        blooms_tag=blooms_tag,
    )
    return None, redirect(reverse('askup:qset', kwargs={'pk': qset.id}))
