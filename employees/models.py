from django.db import models
from django.contrib.auth.models import User
from employees.models import *
import employees.models


class TemporaryPassword(models.Model):
    id = models.BigAutoField(primary_key=True)
    expiration = models.DateTimeField()
    password = models.CharField(max_length=2000, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)


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
    employer = models.CharField(max_length=100)  # dont use, use employment_company instead
    pin = models.IntegerField(null=True, blank=True)
    date_added = models.DateField(null=False, blank=False)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[("Male", "Male"), ("Female", "Female"),("Unassigned", "Unassigned"),("Select", "Select")], default="Select")
    height = models.CharField(max_length=100,null=True, blank=True)
    weight = models.CharField(max_length=100, null=True, blank=True)
    employment_company = models.ForeignKey(Employers, on_delete=models.CASCADE, null=True)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class EmployeeJob(models.Model):
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    job = models.ForeignKey(
        'jobs.Jobs', on_delete=models.PROTECT, null=True, blank=True)

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
    user = models.ForeignKey(Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)


class CertificationCategories(models.Model):
    id = models.BigAutoField(primary_key=True)
    # OSHA30, dbids card, tuburculosis, CRMC, Respirator Clearance
    description = models.CharField(null=True, max_length=200)
    expiration_days = models.IntegerField(default=0)

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
    user = models.ForeignKey(Employees, on_delete=models.PROTECT)
    note = models.CharField(null=True, max_length=2000)


class CertificationActionRequired(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(null=True, max_length=200)
    main = models.ForeignKey(Certifications, on_delete=models.PROTECT)

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

class ToolboxTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=2000, blank=True, null=True)

class ScheduledToolboxTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    master = models.ForeignKey(ToolboxTalks, on_delete=models.PROTECT, null=True)
    date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=2000, blank=True, null=True) #use this only for a custom one

class CompletedToolboxTalks(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(null=True, blank=True)
    employee = models.ForeignKey(Employees, on_delete=models.PROTECT)
    master = models.ForeignKey(ScheduledToolboxTalks, on_delete=models.PROTECT)

class RespiratorClearance(models.Model):
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(Employees, on_delete=models.CASCADE)
    date_created = models.DateField(null=True, blank=True)
    date_completed = models.DateField(null=True, blank=True)
    is_physician_required = models.BooleanField(default=False) #this is true if the employee requested it
    is_physician_actually_required = models.BooleanField(default=False)
    physician_approved = models.BooleanField(default=False)
    approved_for_use = models.BooleanField(default=False)
    date_approved = models.DateField(blank=True, null=True)
    certification = models.ForeignKey(Certifications, on_delete=models.CASCADE, null=True)

class RespiratorClearance1(models.Model):
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    do_you_smoke = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    how_many_cigarettes = models.IntegerField(default=0, blank=True, null=True)
    how_many_years = models.IntegerField(default=0, blank=True, null=True)
    do_you_have_seizures = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    seizures_year_diagnosed = models.IntegerField(default=0, blank=True, null=True)
    seizures_difficulties = models.CharField(max_length=2000, blank=True, null=True)
    do_you_have_diabetes = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    diabetes_year_diagnosed = models.IntegerField(default=0, blank=True, null=True)
    diabetes_difficulties = models.CharField(max_length=2000, blank=True, null=True)
    allergic_reactions = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    claustrophobia = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    trouble_smelling = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    asbestosis = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    asthma = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    chronic_bronchitis = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    emphysema = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    pneumonia = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    tuberculosis = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    silicosis = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    pneumothorax = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    lung_cancer = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    broken_ribs = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    chest_injuries = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other_lung_problems = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    lung_problem_explanation = models.CharField(max_length=2000, blank=True, null=True)

class RespiratorClearance2(models.Model):
    #PAGE 7
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    breath_shortness = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    coughing_issues = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    wheezing_issues = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    chest_pain = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other_lung_problems = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    lung_problem_explanation = models.CharField(max_length=2000, blank=True, null=True)
    heart_attack = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    stroke = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    angina = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    heart_failure = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    swelling = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    arrhythmia = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    high_blood_pressure = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other_heart_problem = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    heart_problem_explanation = models.CharField(max_length=2000, blank=True, null=True)


class RespiratorClearance3(models.Model):
    # page 11
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    chest_pain = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    heart_skipping = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    heartburn = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    explanation = models.CharField(max_length=2000, blank=True, null=True)
    #page 12
    breathing_medication = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    heart_medication = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    blood_pressure_medication = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    seizure_medication = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    medication_explanation = models.CharField(max_length=2000, blank=True, null=True)


class RespiratorClearance4(models.Model):
    #page 13
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    worn_respirator = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    respirator_type = models.CharField(max_length=2000, blank=True, null=True)
    eye_irritation = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("N/A", "Not Applicable"),("Please Select", "Please Select")], default="Please Select")
    allergies = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("N/A", "Not Applicable"),("Please Select", "Please Select")], default="Please Select")
    anxiety = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("N/A", "Not Applicable"),("Please Select", "Please Select")], default="Please Select")
    weakness = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("N/A", "Not Applicable"),("Please Select", "Please Select")], default="Please Select")
    other_problem = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("N/A", "Not Applicable"),("Please Select", "Please Select")], default="Please Select")
    explanation = models.CharField(max_length=2000, blank=True, null=True)



class RespiratorClearance5(models.Model):
    #page 14
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    home_exposure = models.CharField(max_length=20,
                                choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")],
                                default="Please Select")
    home_exposure_explained = models.CharField(max_length=2000, blank=True, null=True)
    asbestos = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    silica = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    tungsten_cobalt = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    beryllium = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    aluminum = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    coal = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    iron = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    tin = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    dusty_environments = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other_exposure = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    explanation = models.CharField(max_length=2000, blank=True, null=True)


class RespiratorClearance6(models.Model):
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    #page 16
    second_job = models.CharField(max_length=2000, blank=True, null=True)
    previous_occupations = models.CharField(max_length=2000, blank=True, null=True)
    hobbies = models.CharField(max_length=2000, blank=True, null=True)
    military_exposure = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    hazmat_team = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    other_medications = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")], default="Please Select")
    list_medications = models.CharField(max_length=2000, blank=True, null=True)
    physician = models.CharField(max_length=20, choices=[("Yes", "Yes"), ("No", "No"), ("Please Select", "Please Select")],default="Please Select")


class RespiratorNotes(models.Model):
    id = models.BigAutoField(primary_key=True)
    main = models.ForeignKey(RespiratorClearance, on_delete=models.CASCADE)
    date = models.DateField()
    employee = models.ForeignKey(Employees, on_delete=models.CASCADE)
    note = models.CharField(max_length=2000, blank=True, null=True)
