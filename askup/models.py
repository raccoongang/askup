"""Askup django models."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Qset(models.Model):
    """Describes the Qset (questions set) and the Organization model and it's behaviour."""

    TYPES = (
        (0, "mixed"),
        (1, "subsets only"),
        (2, "questions only"),
    )
    name = models.CharField(max_length=255, db_index=True)
    type = models.PositiveSmallIntegerField(choices=TYPES, default=1)
    """top_qset (an organization) is a qset on the top of the tree"""
    top_qset = models.ForeignKey(
        "self",
        related_name="organization_qsets",
        on_delete=models.CASCADE,
        null=True,
        blank=False
    )
    parent_qset = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    for_any_authenticated = models.BooleanField(default=False, db_index=True)
    for_unauthenticated = models.BooleanField(default=False, db_index=True)
    show_authors = models.BooleanField(default=True)
    own_questions_only = models.BooleanField(default=False)
    users = models.ManyToManyField(User, blank=True)
    questions_count = models.PositiveIntegerField(default=0, db_index=True)

    def __init__(self, *args, **kwargs):
        """Initialize the Qset model object."""
        super().__init__(*args, **kwargs)
        self._previous_parent_qset_id = self.parent_qset_id

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save the object updates into the DB.

        Overriding the models.Model save method.
        """
        is_organization = self.parent_qset_id is None
        is_new = self.id is None

        if is_new:
            if is_organization:
                super().save(*args, **kwargs)  # acquire an id (save into the DB)
                self.top_qset_id = self.id
            else:
                self.top_qset_id = self.parent_qset.top_qset_id

            super().save(*args, **kwargs)
            return

        if is_organization:
            super().save(*args, **kwargs)
            return

        if self.parent_qset_id != self._previous_parent_qset_id and self.questions_count != 0:
            try:
                previous_parent = Qset.objects.get(id=self._previous_parent_qset_id)
                previous_parent.iterate_questions_count(-self.questions_count)
                previous_parent.save()
            except models.Model.DoesNotExist:
                pass

            self.top_qset_id = self.get_parent_organization()
            self.parent_qset.iterate_questions_count(self.questions_count)

        self._previous_parent_qset_id = self.parent_qset_id
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Delete the object from the DB.

        Overriding the models.Model delete method.
        """
        if self.parent_qset_id is None:
            # If it's an Organization object
            super().delete(*args, **kwargs)
            return

        if self.parent_qset.parent_qset_id is None:
            # If parent qset is an Organization object
            self.parent_qset.iterate_questions_count(-self.questions_count)
        else:
            # ...else move all the child questions into it
            for question in self.question_set.all():
                question.qset_id = self.parent_qset_id
                question.save()

        super().delete(*args, **kwargs)

    def iterate_questions_count(self, amount):
        """
        Iterate questions_count recursively.

        Iterate questions_count on a specific amount
        recursively from the self to the top parent
        (organization).
        """
        if (self.questions_count + amount) < 0:
            self.questions_count = amount
        else:
            self.questions_count += amount

        if self.parent_qset_id:
            self.parent_qset.iterate_questions_count(amount)

        self.save()

    def validate_unique(self, exclude=None):
        """
        Validate the Qset model object uniqueness.

        Overriding the models.Model method.
        """
        if self.parent_qset_id is None:
            is_exists = Qset.objects.exclude(id=self.id).filter(
                name=self.name,
                parent_qset_id__isnull=True
            ).exists()

            if is_exists:
                raise ValidationError("Organization with such name is already exists")

        super().validate_unique(exclude)

    def __str__(self):
        """Return a string representation of a Qset object."""
        return self.name

    def get_parent_organization(self):
        """
        Return an actual organization of this qset tree.

        Returns an organization of the first parent qset.
        If there's no parent qset then returns the id of itself.
        """
        if self.parent_qset is None:
            return self.id
        else:
            return self.parent_qset.top_qset_id

    def get_parents(self):
        """Collect parents data for the breadcrumbs composing."""
        parents = []
        parent = self.parent_qset

        while parent:
            if parent.parent_qset is None:
                parents.append(('askup:organization', parent.id, parent.name))
            else:
                parents.append(('askup:qset', parent.id, parent.name))

            parent = parent.parent_qset

        parents.reverse()
        return parents

    class Meta:
        unique_together = ('parent_qset', 'name')


class Organization(Qset):
    """Describes the Organization model and it's behaviour."""

    def __str__(self):
        """Return a string representation of an Organization object."""
        return self.name


class EmailPattern(models.Model):
    """Contains all the email patterns of the organizations."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True
    )
    text = models.CharField(max_length=50)


class Question(models.Model):
    """Describes all the Qset's and the Organization's models and their behaviours."""

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
    qset = models.ForeignKey(Qset, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, db_column='author_id', on_delete=models.CASCADE, default=0)
    blooms_tag = models.PositiveSmallIntegerField(
        choices=BLOOMS_TAGS,
        null=True,
        blank=True,
        default=None
    )

    def __init__(self, *args, **kwargs):
        """Initialize the Question model object."""
        super().__init__(*args, **kwargs)
        self._previous_qset_id = self.qset_id

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save the object updates into the DB.

        Overriding the models.Model save method.
        """
        super().save(*args, **kwargs)

        if self.qset_id != self._previous_qset_id:
            # Process the case when the question is just created
            if self._previous_qset_id:
                previous_parent = Qset.objects.get(id=self._previous_qset_id)
                previous_parent.iterate_questions_count(-1)
                previous_parent.save()

            self.qset.iterate_questions_count(1)
            super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Delete the object from the DB.

        Overriding the models.Model delete method.
        """
        self.qset.iterate_questions_count(-1)
        super().delete(*args, **kwargs)

    def __str__(self):
        """Return a string representation of a Question object."""
        return self.text


class Answer(models.Model):
    """Describes a student answer model and it's behaviour."""

    EVALUATIONS = (
        (0, "wrong"),
        (1, "sort-of"),
        (2, "correct"),
    )
    text = models.CharField(max_length=255)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, db_column='author_id', on_delete=models.CASCADE)
    self_evaluation = models.PositiveSmallIntegerField(choices=EVALUATIONS)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        """Return a string representation of an Answer object."""
        return self.text


class Vote(models.Model):
    """Describes a vote model and it's behaviour."""

    VOTES = (
        (-1, 'vote down'),
        (1, 'vote up')
    )
    value = models.SmallIntegerField(choices=VOTES)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ('question', 'voter')
