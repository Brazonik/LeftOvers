# Generated by Django 4.2.18 on 2025-03-20 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_achievement_userpoints_current_level_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usernotification',
            name='notification_type',
            field=models.CharField(default='info', max_length=50),
        ),
    ]
