# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2024-08-18 19:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cabinets', '0001_initial'),
        ('sapitwa', '0008_tempdocument_quotation_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='tempdocument',
            name='cabinet',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='cabinets.Cabinet'),
        ),
    ]
