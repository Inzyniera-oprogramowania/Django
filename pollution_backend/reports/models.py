import sys
import os
from uuid import uuid4
from django.utils.timezone import now
from django.db import models

def report_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    safe_title = "export"
    new_filename = f"{safe_title}_{uuid4().hex[:8]}.{ext}"
    date_path = now().strftime("%Y/%m")
    user_id = getattr(instance.advanced_user, 'id', 0) 
    return os.path.join(f"reports/user_{user_id}/{date_path}", new_filename)

class Report(models.Model):
    title = models.CharField(max_length=255)
    created_at = models.DateField()
    results = models.JSONField(default=dict)
    advanced_user = models.ForeignKey(
        "users.AdvancedUser",
        on_delete=models.RESTRICT,
        db_column="advanceduserid",
    )
    parameters = models.JSONField(default=dict, blank=True, db_column="parameters")

    class Meta:
        db_table = "report"
        managed = True
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class ReportIssue(models.Model):
    report = models.ForeignKey(
        Report, 
        on_delete=models.CASCADE, 
        related_name='issues' 
    )
    user = models.ForeignKey(
        "users.AdvancedUser",
        on_delete=models.SET_NULL,
        null=True
    )
    reported_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(help_text="Opis problemu z integralnością danych")
    
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "report_issue"
        ordering = ['-reported_at']

    def __str__(self):
        return f"Issue for Report {self.report.id}: {self.description[:30]}..."
