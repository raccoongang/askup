from askup.models import Question


def check_user_and_create_question(user, qset, text, answer_text, blooms_tag):
    """
    Check user permissions create question.

    Returns object if operation was successfuly executed otherwise returns redirect object.
    """
    return Question.objects.create(
        text=text,
        answer_text=answer_text,
        qset_id=qset.id,
        user_id=user.id,
        blooms_tag=blooms_tag,
    )
