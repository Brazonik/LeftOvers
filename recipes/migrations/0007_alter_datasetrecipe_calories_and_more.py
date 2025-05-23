# Generated by Django 4.2.18 on 2025-02-13 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_datasetrecipe_remove_recipe_author_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetrecipe',
            name='calories',
            field=models.FloatField(db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name='datasetrecipe',
            name='category',
            field=models.CharField(db_index=True, default='Uncategorized', max_length=100),
        ),
        migrations.AlterField(
            model_name='datasetrecipe',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='datasetrecipe',
            name='name',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AddIndex(
            model_name='datasetrecipe',
            index=models.Index(fields=['name'], name='recipes_dat_name_b6319f_idx'),
        ),
        migrations.AddIndex(
            model_name='datasetrecipe',
            index=models.Index(fields=['category'], name='recipes_dat_categor_b4c501_idx'),
        ),
        migrations.AddIndex(
            model_name='datasetrecipe',
            index=models.Index(fields=['calories'], name='recipes_dat_calorie_7b391c_idx'),
        ),
        migrations.AddIndex(
            model_name='datasetrecipe',
            index=models.Index(fields=['created_at'], name='recipes_dat_created_f3f4b0_idx'),
        ),
    ]
