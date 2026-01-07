from django.db import models


class Report(models.Model):
    title = models.CharField(max_length=255)
    created_at = models.DateField()
    file_url = models.CharField(max_length=500, blank=True, null=True)  # noqa: DJ001
    advanced_user = models.ForeignKey(
        "users.AdvancedUser",
        on_delete=models.RESTRICT,
        db_column="advanceduserid",
    )

    class Meta:
        db_table = "report"
        managed = False

    def __str__(self):
        return self.title


class ReportScope(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, db_column="reportid")
    pollutant = models.ForeignKey(
        "sensors.Pollutant",
        on_delete=models.RESTRICT,
        db_column="pollutantid",
    )

    class Meta:
        db_table = "reportscope"
        managed = False

    def __str__(self):
        return f"{self.report.title} - {self.pollutant}"
