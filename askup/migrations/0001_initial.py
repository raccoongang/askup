# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-31 16:40
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255)),
                ('self_evaluation', models.PositiveSmallIntegerField(choices=[(0, 'wrong'), (1, 'sort-of'), (2, 'correct')], null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='EmailPattern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Qset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('type', models.PositiveSmallIntegerField(choices=[(0, 'mixed'), (1, 'subsets only'), (2, 'questions only')], default=2)),
                ('for_any_authenticated', models.BooleanField(db_index=True, default=False)),
                ('for_unauthenticated', models.BooleanField(db_index=True, default=False)),
                ('show_authors', models.BooleanField(default=True)),
                ('own_questions_only', models.BooleanField(default=False)),
                ('questions_count', models.PositiveIntegerField(db_index=True, default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(db_index=True)),
                ('answer_text', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('blooms_tag', models.PositiveSmallIntegerField(blank=True, choices=[(0, 'remembering'), (1, 'understanding'), (2, 'applying'), (3, 'analyzing'), (4, 'evaluating'), (5, 'creating')], default=None, null=True)),
                ('vote_value', models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.SmallIntegerField(choices=[(-1, 'vote down'), (1, 'vote up')])),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='askup.Question')),
                ('voter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('qset_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='askup.Qset')),
            ],
            bases=('askup.qset',),
        ),
        migrations.AddField(
            model_name='question',
            name='qset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='askup.Qset'),
        ),
        migrations.AddField(
            model_name='question',
            name='user',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='qset',
            name='parent_qset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='askup.Qset'),
        ),
        migrations.AddField(
            model_name='qset',
            name='top_qset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='organization_qsets', to='askup.Qset'),
        ),
        migrations.AddField(
            model_name='qset',
            name='users',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='answer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='askup.Question'),
        ),
        migrations.AddField(
            model_name='answer',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([('question', 'voter')]),
        ),
        migrations.AlterUniqueTogether(
            name='question',
            unique_together=set([('text', 'qset')]),
        ),
        migrations.AlterUniqueTogether(
            name='qset',
            unique_together=set([('parent_qset', 'name')]),
        ),
        migrations.AddField(
            model_name='emailpattern',
            name='organization',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='askup.Organization'),
        ),
    ]
