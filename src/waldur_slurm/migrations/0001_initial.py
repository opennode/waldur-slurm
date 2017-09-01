# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-01 08:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields
import nodeconductor.core.fields
import nodeconductor.core.models
import nodeconductor.core.validators
import nodeconductor.logging.loggers
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('structure', '0052_customer_subnets'),
    ]

    operations = [
        migrations.CreateModel(
            name='Allocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('description', models.CharField(blank=True, max_length=500, verbose_name='description')),
                ('name', models.CharField(max_length=150, validators=[nodeconductor.core.validators.validate_name], verbose_name='name')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('error_message', models.TextField(blank=True)),
                ('state', django_fsm.FSMIntegerField(choices=[(5, 'Creation Scheduled'), (6, 'Creating'), (1, 'Update Scheduled'), (2, 'Updating'), (7, 'Deletion Scheduled'), (8, 'Deleting'), (3, 'OK'), (4, 'Erred')], default=5)),
                ('backend_id', models.CharField(blank=True, max_length=255)),
                ('cpu', models.FloatField()),
            ],
            options={
                'abstract': False,
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.core.models.BackendModelMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.CreateModel(
            name='SLURMService',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', nodeconductor.core.fields.UUIDField()),
                ('available_for_all', models.BooleanField(default=False, help_text='Service will be automatically added to all customers projects if it is available for all')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.Customer', verbose_name='organization')),
            ],
            options={
                'verbose_name': 'SLURM provider',
                'verbose_name_plural': 'SLURM providers',
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.CreateModel(
            name='SLURMServiceProjectLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.Project')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='waldur_slurm.SLURMService')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'SLURM provider project link',
                'verbose_name_plural': 'SLURM provider project links',
            },
            bases=(nodeconductor.core.models.DescendantMixin, nodeconductor.logging.loggers.LoggableMixin, models.Model),
        ),
        migrations.AddField(
            model_name='slurmservice',
            name='projects',
            field=models.ManyToManyField(related_name='_slurmservice_projects_+', through='waldur_slurm.SLURMServiceProjectLink', to='structure.Project'),
        ),
        migrations.AddField(
            model_name='slurmservice',
            name='settings',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='structure.ServiceSettings'),
        ),
        migrations.AddField(
            model_name='allocation',
            name='service_project_link',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='allocations', to='waldur_slurm.SLURMServiceProjectLink'),
        ),
        migrations.AddField(
            model_name='allocation',
            name='tags',
            field=taggit.managers.TaggableManager(blank=True, help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
        migrations.AlterUniqueTogether(
            name='slurmserviceprojectlink',
            unique_together=set([('service', 'project')]),
        ),
        migrations.AlterUniqueTogether(
            name='slurmservice',
            unique_together=set([('customer', 'settings')]),
        ),
    ]
