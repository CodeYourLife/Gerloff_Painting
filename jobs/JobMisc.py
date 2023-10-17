import console.misc
from jobs.models import *
from employees.models import *
from console.misc import Email
from datetime import date
from django.contrib.auth.models import User

def start_date_change(job, newdate, status, note, author,did_date_change):
    # status is 1- active, 2- not active, 3 - no change
    statusnote = ""
    if status == 1:
        job.is_active = True
        statusnote = "Changed Status to Active"
    if status == 2:
        job.is_active = False
        statusnote = "Changed Status to Inactive"
    if did_date_change == True:
        job.start_date = newdate
        job.start_date_checked = date.today()
        JobNotes.objects.create(job_number=job, note="Start Date Changed to " + newdate + ". " + note + ". " + statusnote,
                                type="auto_start_date_note", user=author, date=date.today())
    else:
        JobNotes.objects.create(job_number=job, note=statusnote + ". " + note,
                                type="auto_start_date_note", user=author, date=date.today())
    job.save()


def gerloff_super_change(job, superintendent, author):
    JobNotes.objects.create(job_number=job, note="Superintendent " + str(superintendent) + " Assigned to " + str(job),
                            type="auto_misc_note",
                            user=author, date=date.today())
    job.superintendent = superintendent
    email_body = str(superintendent) + "\n You have been assigned to \n" + str(job.job_number)+ "\n" + str(job) + "\n" + str(job.client.company)
    Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com', False)
    job.save()
