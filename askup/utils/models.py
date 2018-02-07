from django.shortcuts import redirect
from django.urls import reverse

from askup.models import Question
from .general import check_user_has_groups


def check_user_and_create_question(user, qset, text, answer_text, blooms_tag):
    """
    Check user permissions create question.

    Returns True if operation was successfuly executed otherwise returns redirect object.
    """
    if not check_user_has_groups(user, 'admin') and user not in qset.top_qset.users.all():
        return redirect(reverse('askup:organizations'))

    Question.objects.create(
        text=text,
        answer_text=answer_text,
        qset_id=qset.id,
        user_id=user.id,
        blooms_tag=blooms_tag,
    )

    return True
