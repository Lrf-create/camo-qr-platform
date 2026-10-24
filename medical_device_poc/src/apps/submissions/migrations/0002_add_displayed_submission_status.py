# Generated manually for DISPLAYED submission status.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="portasubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("EDITING", "编辑中"),
                    ("READY", "待处理"),
                    ("PROCESSING", "处理中"),
                    ("SUCCESS", "成功"),
                    ("DISPLAYED", "已展示"),
                    ("BUSINESS_FAILED", "业务失败"),
                    ("DATA_ERROR", "数据错误"),
                ],
                default="EDITING",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="portbsubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("EDITING", "编辑中"),
                    ("READY", "待处理"),
                    ("PROCESSING", "处理中"),
                    ("SUCCESS", "成功"),
                    ("DISPLAYED", "已展示"),
                    ("BUSINESS_FAILED", "业务失败"),
                    ("DATA_ERROR", "数据错误"),
                ],
                default="EDITING",
                max_length=32,
            ),
        ),
    ]
