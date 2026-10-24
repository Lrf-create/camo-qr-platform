from __future__ import annotations

from django.db import models


class SubmissionStatus(models.TextChoices):
    EDITING = "EDITING", "编辑中"
    READY = "READY", "待处理"
    PROCESSING = "PROCESSING", "处理中"
    SUCCESS = "SUCCESS", "成功"
    DISPLAYED = "DISPLAYED", "已展示"
    BUSINESS_FAILED = "BUSINESS_FAILED", "业务失败"
    DATA_ERROR = "DATA_ERROR", "数据错误"


class BaseSubmission(models.Model):
    session_id = models.UUIDField(unique=True)
    qr_token_raw = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=SubmissionStatus.choices, default=SubmissionStatus.EDITING)
    result_code = models.CharField(max_length=64, blank=True)
    result_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]


class PortASubmission(BaseSubmission):
    class Meta(BaseSubmission.Meta):
        db_table = "port_a_submission"
        indexes = [models.Index(fields=["status", "created_at"], name="idx_port_a_status_created")]


class PortBSubmission(BaseSubmission):
    class Meta(BaseSubmission.Meta):
        db_table = "port_b_submission"
        indexes = [models.Index(fields=["status", "created_at"], name="idx_port_b_status_created")]


class BaseSubmissionItem(models.Model):
    type = models.CharField(max_length=64, db_column="TYPE")
    num = models.PositiveIntegerField(default=0, db_column="NUM")

    class Meta:
        abstract = True
        ordering = ["type"]


class PortASubmissionItem(BaseSubmissionItem):
    submission = models.ForeignKey(PortASubmission, on_delete=models.CASCADE, related_name="items")

    class Meta(BaseSubmissionItem.Meta):
        db_table = "port_a_submission_item"
        constraints = [
            models.UniqueConstraint(fields=["submission", "type"], name="uq_port_a_submission_type"),
        ]


class PortBSubmissionItem(BaseSubmissionItem):
    submission = models.ForeignKey(PortBSubmission, on_delete=models.CASCADE, related_name="items")

    class Meta(BaseSubmissionItem.Meta):
        db_table = "port_b_submission_item"
        constraints = [
            models.UniqueConstraint(fields=["submission", "type"], name="uq_port_b_submission_type"),
        ]
