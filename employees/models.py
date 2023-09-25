from django.db import models
from django.contrib.auth.models import User
from employees.models import *


class Employers(models.Model):
    id = models.BigAutoField(primary_key=True)
    company_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.company_name}"


class EmployeeTitles(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.description}"


class EmployeeLevels(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=50)
    pay_rate = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.description}"


class GPUserAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pinEntryDate = models.DateTimeField(blank=False, auto_now_add=True)
    pin = models.IntegerField(blank=False, unique=True)


class Employees(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee_number = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    first_name = models.CharField(null=True, max_length=50)
    middle_name = models.CharField(null=True, blank=True, max_length=50)
    last_name = models.CharField(null=True, max_length=50)
    phone = models.CharField(null=True, max_length=50, blank=True)
    email = models.EmailField(null=True, blank=True)
    level = models.ForeignKey(
        EmployeeLevels, on_delete=models.PROTECT, null=True, blank=True)
    nickname = models.CharField(null=True, max_length=50, blank=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)
    job_title = models.ForeignKey(EmployeeTitles, on_delete=models.CASCADE, null=True)
    employer = models.CharField(max_length=100)  # Gerloff Painting, Nam, JuarezPro, etc.
    pin = models.IntegerField(null=True, blank=True)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Metrics(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=1000)  # Brush/Roll, Spray

    def __str__(self):
        return f"{self.description}"

    def total_numbers(self):
        totalnumbers = -1
        for x in MetricCategories.objects.filter(metric=self):
            totalnumbers = totalnumbers + 1
        return totalnumbers


class MetricAssessment(models.Model):
    id = models.BigAutoField(primary_key=True)
    reviewer = models.ForeignKey(Employees, on_delete=models.PROTECT)
    date = models.DateField()
    note = models.CharField(max_length=2000, blank=True, null=True)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.date} {self.reviewer}"


class DailyReports(models.Model):
    id = models.BigAutoField(primary_key=True)
    foreman = models.ForeignKey(Employees, on_delete=models.PROTECT)
    date = models.DateField()
    note = models.CharField(max_length=2000, null=True, blank=True)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.foreman} {self.date}"


class EmployeeReview(models.Model):
    id = models.BigAutoField(primary_key=True)
    assessment = models.ForeignKey(
        MetricAssessment, on_delete=models.PROTECT, null=True, blank=True)
    daily_report = models.ForeignKey(
        DailyReports, on_delete=models.PROTECT, null=True, blank=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)

    def __str__(self):
        if self.assessment != None:
            return f"{self.assessment} {self.employee}"
        else:
            return f"{self.daily_report} {self.employee}"


class TrainingTopic(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=2000)  # spray training
    details = models.CharField(max_length=2000)  # class syllabus / outline
    assessment_category = models.ForeignKey(
        Metrics, on_delete=models.PROTECT, related_name="class1", null=True, blank=True)
    assessment_category1 = models.ForeignKey(
        Metrics, on_delete=models.PROTECT, related_name="class2", null=True, blank=True)

    def __str__(self):
        return f"{self.description}"


class ClassOccurrence(models.Model):
    id = models.BigAutoField(primary_key=True)
    topic = models.ForeignKey(
        TrainingTopic, on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField(max_length=500)
    date = models.DateField()
    teacher = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True, blank=True)
    teacher2 = models.CharField(max_length=100, null=True, blank=True)
    note = models.CharField(max_length=2000, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.description} {self.date}"


class ClassAttendees(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_event = models.ForeignKey(ClassOccurrence, on_delete=models.PROTECT)
    student = models.ForeignKey(
        Employees, on_delete=models.PROTECT, null=True, blank=True)
    student2 = models.CharField(max_length=100, null=True, blank=True)
    note = models.CharField(max_length=2000, null=True, blank=True)


class Exam(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=500)  # spray exam
    details = models.CharField(max_length=2000)  # spray exam
    max_score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.description}"


class ExamScore(models.Model):
    id = models.BigAutoField(primary_key=True)
    exam = models.ForeignKey(
        Exam, on_delete=models.PROTECT, null=True, blank=True)
    exam2 = models.CharField(max_length=200, null=True, blank=True)
    student = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="student", null=True, blank=True)
    student2 = models.CharField(max_length=100, null=True, blank=True)
    teacher = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="teacher", null=True, blank=True)
    teacher2 = models.CharField(max_length=100, null=True, blank=True)
    score = models.IntegerField(default=0, null=True, blank=True)
    custom_score_max = models.IntegerField(default=0, null=True, blank=True)
    note = models.CharField(max_length=2000, null=True, blank=True)
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} {self.exam} {self.date}"


class SuperWeeklyReport(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField()
    job = models.ForeignKey('jobs.Jobs', on_delete=models.PROTECT)
    superintendent = models.ForeignKey(Employees, on_delete=models.PROTECT)
    total_weekly_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    completed = models.CharField(max_length=2000)
    remaining = models.CharField(max_length=2000)
    issues = models.CharField(max_length=2000)


class SuperReportEmployees(models.Model):
    id = models.BigAutoField(primary_key=True)
    report = models.ForeignKey(SuperWeeklyReport, on_delete=models.PROTECT)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)


class Mentorship(models.Model):
    id = models.BigAutoField(primary_key=True)
    apprentice = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="apprentice")
    mentor = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="mentor")
    start_date = models.DateField()
    note = models.CharField(max_length=2000, null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.mentor} {self.apprentice}"


class MentorshipNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    mentorship = models.ForeignKey(Mentorship, on_delete=models.PROTECT)
    date = models.DateField()
    user = models.CharField(null=True, max_length=200)
    note = models.CharField(null=True, max_length=2000)


class CertificationCategories(models.Model):
    id = models.BigAutoField(primary_key=True)
    # OSHA30, dbids card, tuburculosis, CRMC
    description = models.CharField(null=True, max_length=200)

    def __str__(self):
        return f"{self.description}"


class Certifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(
        CertificationCategories, on_delete=models.PROTECT, null=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    description = models.CharField(null=True, blank=True, max_length=500)
    date_received = models.DateField(null=True, blank=True)
    date_expires = models.DateField(null=True, blank=True)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)
    note = models.CharField(null=True, blank=True, max_length=2000)
    is_closed = models.BooleanField(default=False)
    action_required = models.BooleanField(default=False)
    action = models.CharField(null=True, blank=True, max_length=500)

    def __str__(self):
        return f"{self.category} {self.employee}"


class CertificationNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    certification = models.ForeignKey(
        Certifications, on_delete=models.PROTECT, null=True)
    date = models.DateField()
    user = models.CharField(null=True, max_length=200)
    note = models.CharField(null=True, max_length=2000)


class CertificationActionRequired(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(null=True, max_length=200)

    def __str__(self):
        return f"{self.action}"


class WriteUp(models.Model):
    id = models.BigAutoField(primary_key=True)
    supervisor = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="Supervisor")
    employee = models.ForeignKey(
        Employees, on_delete=models.PROTECT, related_name="Employee")
    date = models.DateField()
    description = models.CharField(max_length=100)
    note = models.CharField(max_length=2000, null=True, blank=True)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.date} {self.employee} {self.description}"


class WriteUpDefaults(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.description}"


class Vacation(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    vacation_date = models.DateField()
    duration = models.IntegerField(default=0)
    employee_note = models.CharField(max_length=2000)
    is_approved = models.BooleanField(default=False)
    request_date = models.DateField()


class VacationApprovers(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)


class ApprovedVacations(models.Model):
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(Vacation, on_delete=models.PROTECT)
    date_sent = models.DateField()
    approver = models.ForeignKey(Employees, on_delete=models.PROTECT)
    is_approved = models.BooleanField(default=False)
    approver_notes = models.CharField(max_length=2000)


class DailyReportEmployees(models.Model):
    id = models.BigAutoField(primary_key=True)
    report = models.ForeignKey(DailyReports, on_delete=models.PROTECT)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)


class MetricCategories(models.Model):
    id = models.BigAutoField(primary_key=True)
    number = models.IntegerField(default=0)
    metric = models.ForeignKey(Metrics, on_delete=models.PROTECT)
    # 1 = none 2 = learning puttying materials 3 = proficient
    description = models.CharField(max_length=1000)

    def __str__(self):
        return f"{self.metric} {self.number}"


class MetricLevels(models.Model):
    id = models.BigAutoField(primary_key=True)
    level = models.ForeignKey(EmployeeLevels, on_delete=models.PROTECT)
    metric = models.ForeignKey(Metrics, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.metric} {self.level}"


class ProductionCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    item1 = models.CharField(max_length=200)
    item2 = models.CharField(max_length=200, null=True, blank=True)
    item3 = models.CharField(max_length=200, null=True, blank=True)
    task = models.CharField(max_length=200, null=True, blank=True)
    unit1 = models.CharField(max_length=200, null=True, blank=True)
    unit2 = models.CharField(max_length=200, null=True, blank=True)
    unit3 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.item1} {self.item2} {self.item3} {self.task}"


class MetricAssessmentItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    assessment = models.ForeignKey(
        EmployeeReview, on_delete=models.PROTECT, null=True, blank=True)
    note = models.CharField(max_length=2000, null=True, blank=True)
    category = models.ForeignKey(MetricCategories, on_delete=models.PROTECT)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.assessment} {self.employee}"


class ProductionItems(models.Model):
    id = models.BigAutoField(primary_key=True)
    value1 = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    value2 = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    value3 = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    unit = models.CharField(max_length=20, blank=True, null=True)  # gals
    unit2 = models.CharField(max_length=20, blank=True, null=True)  # sf
    unit3 = models.CharField(max_length=20, blank=True, null=True)  # lf
    note = models.CharField(max_length=2000, blank=True, null=True)
    is_team = models.BooleanField(default=False)
    team_note = models.CharField(max_length=2000, blank=True, null=True)
    hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True)
    daily_report = models.ForeignKey(
        DailyReports, on_delete=models.PROTECT, blank=True, null=True)
    metric_assessment = models.ForeignKey(
        MetricAssessment, on_delete=models.PROTECT, blank=True, null=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    date = models.DateField(null=True, blank=True)
    team_members = models.IntegerField(default=0, null=True, blank=True)
    task = models.ForeignKey(
        ProductionCategory, on_delete=models.PROTECT, blank=True, null=True)
    description = models.CharField(max_length=2000, blank=True, null=True)
    team_number = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.employee} {self.date}"
