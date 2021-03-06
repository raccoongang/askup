"""Askup django models."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.db.models.expressions import RawSQL
from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils.general import check_user_has_groups


class Profile(models.Model):
    """
    Handles the User profile functionality.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)

    def __str__(self):
        """
        Return string representation of the model.

        Used in admin user form to represent an inline, the Profile, part of user form.
        """
        return self.user.username


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    """
    Receive a post_save signal from User model and update the profile.
    """
    if created:
        Profile.objects.create(user=instance)

    instance.profile.save()


class Qset(models.Model):
    """Describes the Qset (questions set) and the Organization model and it's behaviour."""

    TYPES = (
        (0, "mixed"),
        (1, "subjects only"),
        (2, "questions only"),
    )
    name = models.CharField(max_length=255, db_index=True)
    type = models.PositiveSmallIntegerField(choices=TYPES, default=2)
    # top_qset (an organization) is a qset on the top of the tree
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
        blank=True,
        verbose_name="Organization",
    )
    for_any_authenticated = models.BooleanField(default=False, db_index=True)
    for_unauthenticated = models.BooleanField(default=False, db_index=True)
    show_authors = models.BooleanField(default=True)
    own_questions_only = models.BooleanField(default=False)
    users = models.ManyToManyField(User, blank=True)
    questions_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        unique_together = ('parent_qset', 'name')
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

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

        if self.process_new_qset_and_organization_save(is_organization, args, kwargs):
            return

        self.process_parent_qset_changed_save()
        self._previous_parent_qset_id = self.parent_qset_id
        super().save(*args, **kwargs)

    def process_new_qset_and_organization_save(self, is_organization, args, kwargs):
        """Process new qset save."""
        is_new = self.id is None

        if is_new:
            if is_organization:
                super().save(*args, **kwargs)  # acquire an id (save into the DB)
                self.top_qset_id = self.id
            else:
                self.top_qset_id = self.parent_qset.top_qset_id

            super().save(*args, **kwargs)
            return True

        if is_organization:
            self.parent_qset_id = self._previous_parent_qset_id
            super().save(*args, **kwargs)
            return True

        return False

    def process_parent_qset_changed_save(self):
        """Process the parent qset changed save."""
        if self.parent_qset_id != self._previous_parent_qset_id and self.questions_count != 0:
            previous_parent = Qset.objects.filter(id=self._previous_parent_qset_id).first()

            if previous_parent:
                previous_parent.iterate_questions_count(-self.questions_count)
                previous_parent.save()

            self.top_qset_id = self.get_parent_organization()
            self.parent_qset.iterate_questions_count(self.questions_count)

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
        # NOTE(KhaimovMR): Make a comprehensive negative amount protection (recalc tree)
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
        """Return string representation of Qset."""
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

    def get_parents(self, include_itself=False):
        """Collect parents data for the breadcrumbs composing."""
        parents = []

        if include_itself:
            parents.append(('askup:qset', self.id, self.name))

        parent = self.parent_qset

        while parent:
            if parent.parent_qset is None:
                parents.append(('askup:organization', parent.id, parent.name))
            else:
                parents.append(('askup:qset', parent.id, parent.name))

            parent = parent.parent_qset

        parents.reverse()
        return parents

    @classmethod
    def get_user_related_qsets(
        cls,
        user,
        order_by,
        qsets_only=False,
        organizations_only=False,
    ):
        """Return queryset of formatted qsets, permitted to the user."""
        if user and user.id:
            queryset = cls.get_user_related_qsets_queryset(user)
            queryset = queryset.select_related('top_qset')
            queryset = cls.apply_context_related_qsets_filters(
                queryset,
                qsets_only,
                organizations_only,
            )
            queryset = queryset.annotate(
                is_organization=RawSQL('askup_qset.parent_qset_id is null', tuple()),
            )
            queryset = queryset.order_by(*order_by)
        else:
            queryset = Qset.objects.none()

        return queryset

    @classmethod
    def get_user_related_qsets_queryset(cls, user):
        """Return queryset of qset objects for the user related qsets request."""
        return cls.apply_user_related_qsets_filters(user, Qset.objects.all())

    @staticmethod
    def apply_user_related_qsets_filters(user, queryset):
        """Apply user related filters to the queryset."""
        if not check_user_has_groups(user, 'admin'):
            queryset = queryset.filter(top_qset__users=user.id)

        return queryset

    @staticmethod
    def apply_context_related_qsets_filters(queryset, qsets_only, organizations_only):
        """Apply context related filters to the queryset."""
        if qsets_only:
            queryset = queryset.filter(parent_qset_id__gt=0)

        if organizations_only:
            queryset = queryset.filter(parent_qset_id__isnull=True)

        return queryset


class Organization(Qset):
    """Describes the Organization model and it's behaviour."""

    def __str__(self):
        """Return a string representation of an Organization object."""
        return self.name


class Domain(models.Model):
    """Contains all the email patterns of the organizations."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True
    )
    name = models.CharField(max_length=50, unique=False)

    class Meta:
        unique_together = ('organization', 'name')


class QuestionQuerySet(models.query.QuerySet):
    """
    Overrides a question query set class.

    Overriding a question query set class to have a control over
    QuerySet.delete operation (bunch deletion in the admin panel, for example).
    """

    @transaction.atomic
    def delete(self):
        """
        Delete multiple objects.

        Overrides a delete method of the QuerySet class.
        """
        updated_qsets = {}

        for question in self.iterator():
            qset_id = question.qset.id
            updating_qset = updated_qsets.get(qset_id) or question.qset
            updating_qset.iterate_questions_count(-1)
            updated_qsets[qset_id] = updating_qset

        super().delete()


class QuestionObjectManager(models.Manager):
    """
    Overrides a question objects manager.

    Used for the handling with the QuerySet.delete operation
    (bunch deletion in the admin panel, for example).
    """

    def get_queryset(self):
        """
        Return a custom query set.

        Used for the handling with the multiple questions delete operation in admin panel.
        """
        return QuestionQuerySet(self.model, using=self._db)


class Question(models.Model):
    """Describes all the Qset's and the Organization's models and their behaviours."""

    BLOOMS_TAGS = (
        (0, 'remembering'),
        (1, 'understanding'),
        (2, 'applying'),
        (3, 'analyzing'),
        (4, 'evaluating'),
        (5, 'creating')
    )
    text = models.TextField(db_index=True)
    answer_text = models.TextField()
    qset = models.ForeignKey(Qset, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=0)
    blooms_tag = models.PositiveSmallIntegerField(
        choices=BLOOMS_TAGS,
        null=True,
        blank=True,
        default=None
    )
    vote_value = models.IntegerField(default=0)

    objects = QuestionObjectManager()

    class Meta:
        unique_together = ('text', 'qset')

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
        is_new = self.id is None
        super().save(*args, **kwargs)

        if is_new:
            self.qset.iterate_questions_count(1)
            self.vote(self.user_id, 1)
        elif self.qset_id != self._previous_qset_id:
            # Process the case when the question is just created
            if self._previous_qset_id:
                previous_parent = Qset.objects.get(id=self._previous_qset_id)
                previous_parent.iterate_questions_count(-1)
                previous_parent.save()

            self.qset.iterate_questions_count(1)
            self._previous_qset_id = self.qset_id

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Delete the object from the DB.

        Overriding the models.Model delete method.
        """
        self.qset.iterate_questions_count(-1)
        super().delete(*args, **kwargs)

    def vote(self, user_id, value):
        """
        Vote for this question.

        Adds a value to the vote_value of this question as well as creates the vote
        record for the specific user and question in the askup_vote table.
        """
        exists = Vote.objects.filter(question_id=self.id, voter_id=user_id).exists()

        if exists:
            return False, 'You have already voted for this question'

        Vote.objects.create(
            value=value,
            question_id=self.id,
            voter_id=user_id,
        )
        self.vote_value = F('vote_value') + value

        # Saves an object and replaces the F() expression with an actual value
        self.refresh_from_db()

        return self.vote_value, 'Thank you for your vote!'

    def get_votes_aggregated(self):
        """Return votes value of this question aggregated from the askup_vote table."""
        votes = Vote.objects.filter(question_id=self.id).aggregate(models.Sum('value'))
        value = votes['value__sum'] if votes['value__sum'] else 0
        return value

    def __str__(self):
        """Return a string representation of a Question object."""
        return self.text

    @classmethod
    def get_user_related_questions_queryset(cls, user):
        """Return queryset of qset objects for the 'user related qsets' request."""
        return cls.apply_user_related_questions_filters(user, Question.objects.all())

    @staticmethod
    def apply_user_related_questions_filters(user, queryset):
        """Apply user related filters to the queryset."""
        if not check_user_has_groups(user, 'admin'):
            queryset = queryset.filter(qset__top_qset__users=user.id)

        return queryset


class Answer(models.Model):
    """Describes a student answer model and it's behaviour."""

    EVALUATIONS = (
        (0, "wrong"),
        (1, "sort-of"),
        (2, "correct"),
    )
    text = models.TextField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    self_evaluation = models.PositiveSmallIntegerField(choices=EVALUATIONS, null=True)
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

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save the object updates into the DB.

        Overriding the models.Model save method.
        """
        is_new = self.id is None
        super().save(*args, **kwargs)

        if is_new:
            self.question.vote_value += self.value
            self.question.save()

    class Meta:
        unique_together = ('question', 'voter')


class QsetUserSubscription(models.Model):
    """
    Describes the subject user subscription and it's behaviour.

    If object with qset_id and user_id exists in the DB - the user with this id will
    receive scheduled quizes on this subject.
    """

    qset = models.ForeignKey(Qset, on_delete=models.CASCADE, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=0)

    class Meta:
        unique_together = ('qset', 'user')
        verbose_name = 'Subject User Subscription'
        verbose_name_plural = 'Subject User Subscriptions'
