from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Qset(models.Model):
    """Describes the Qset (questions set) and the Organization model and it's behaviour"""
    TYPES = (
        (0, "mixed"),
        (1, "subsets only"),
        (2, "questions only"),
    )
    name = models.CharField(max_length=255, db_index=True)
    type = models.PositiveSmallIntegerField(choices=TYPES, default=1)
    parent_qset = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True
    )
    for_any_authenticated = models.BooleanField(default=False, db_index=True)
    for_unauthenticated = models.BooleanField(default=False, db_index=True)
    show_authors = models.BooleanField(default=True)
    own_questions_only = models.BooleanField(default=False)
    users = models.ManyToManyField(User, blank=True, db_index=True)
    questions_count = models.PositiveIntegerField(default=0, db_index=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        previous_parent_id = self.parent_qset_id
        super().save(*args, **kwargs)

        if (self.parent_qset_id != previous_parent_id
                and self.parent_qset_id
                and self.questions_count != 0):
            previous_parent = Qset.objects.get(id=previous_parent_id)
            previous_parent.iterate_questions_count(-self.questions_count)
            previous_parent.save()
            self.parent_qset.iterate_questions_count(self.questions_count)

        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        self.iterate_questions_count(-self.questions_count)
        super().delete(*args, **kwargs)

    def iterate_questions_count(self, amount):
        """
        Iterate questions_count on a specific amount
        recursively to the top parent (organization)
        """
        self.questions_count += amount

        if self.parent_qset_id:
            self.parent_qset.iterate_questions_count(amount)

        self.save()

    def validate_unique(self, exclude=None):
        if self.parent_qset_id is None:
            is_exists = Qset.objects.exclude(id=self.id).filter(
                name=self.name,
                parent_qset_id__isnull=True
            ).exists()

            if is_exists:
                raise ValidationError("Organization with such name is already exists")

        super().validate_unique(exclude)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('parent_qset', 'name')


class Organization(Qset):
    """Describes the Organization model and it's behaviour"""
    def __str__(self):
        return self.name


class EmailPattern(models.Model):
    """Contains all the email patterns of the organizations"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, db_index=True)
    text = models.CharField(max_length=50, db_index=True)


class Question(models.Model):
    """Describes all the Qset's and the Organization's models and their behaviours"""
    BLOOMS_TAGS = (
        (0, 'remember'),
        (1, 'understand'),
        (2, 'apply'),
        (3, 'analyze'),
        (4, 'evaluate'),
        (5, 'create')
    )
    text = models.TextField(db_index=True)
    answer_text = models.CharField(max_length=255)
    qset = models.ForeignKey(Qset, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    user = models.ForeignKey(User, db_column='author_id', on_delete=models.CASCADE, db_index=True, default=0)
    blooms_tag = models.PositiveSmallIntegerField(
        choices=BLOOMS_TAGS,
        null=True,
        blank=True,
        default=None
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_qset_id = self.qset_id

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.qset_id != self._previous_qset_id:
            # Process the case when the question is just created
            if self._previous_qset_id:
                previous_parent = Qset.objects.get(id=self._original_qset_id)
                previous_parent.iterate_questions_count(-1)
                previous_parent.save()

            self.qset.iterate_questions_count(1)
            super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        self.qset.iterate_questions_count(-1)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.text


class Answer(models.Model):
    """Describes a student answer model and it's behaviour"""
    EVALUATIONS = (
        (0, "wrong"),
        (1, "sort-of"),
        (2, "correct"),
    )
    text = models.CharField(max_length=255)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(User, db_column='author_id', on_delete=models.CASCADE, db_index=True)
    self_evaluation = models.PositiveSmallIntegerField(choices=EVALUATIONS)
    created_at = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    def __str__(self):
        return self.text


class Vote(models.Model):
    """Describes a vote model and it's behaviour"""
    VOTES = (
        (-1, 'vote down'),
        (1, 'vote up')
    )
    value = models.SmallIntegerField(choices=VOTES, db_index=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_index=True)
    voter = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    class Meta:
        unique_together = ('question', 'voter')
