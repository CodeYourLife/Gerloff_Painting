
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import os.path
from django.conf import settings
import requests
from jobs.models import ClockSharkTimeEntry, JobsiteSafetyInspection, JobNotes
from django.db.models import Sum
from employees.models import Employees
from datetime import date
import ipaddress


class Email:
    def sendEmail(title, body, to, filename):
        msg = MIMEMultipart()
        # sender = to
        sender = 'joe@gerloffpainting.com'
        msg['From'] = 'operations@gerloffpainting.com'
        msg['To'] = ", ".join(to)
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        if filename != False:
            att_name = os.path.basename(filename)
            with open(filename, 'rb') as file:
                attach = MIMEApplication(file.read(), _subtype='pdf')
                attach.add_header('Content-Disposition', 'attachment', filename=att_name)
                # attach.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attach)
        text = msg.as_string()
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()

    def sendEmail2(title, body, to, filename):
        msg = MIMEMultipart()
        # sender = to
        sender = 'joe@gerloffpainting.com'
        msg['From'] = 'operations@gerloffpainting.com'
        msg['To'] = ", ".join(to)
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        for f in filename:
            att_name = os.path.basename(f)
            with open(f, 'rb') as file:
                attach = MIMEApplication(file.read(), _subtype='pdf')
                attach.add_header('Content-Disposition', 'attachment', filename=att_name)
                # attach.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attach)
        text = msg.as_string()
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()

def createfolder(subfolder):
        parent_dir = settings.MEDIA_ROOT
        path = os.path.join(parent_dir, subfolder)
        try:
            os.mkdir(path)
        except OSError as error:
            print(error)

def getFilesOrFolders(subfolder, item):
    parent_dir = settings.MEDIA_ROOT
    path = os.path.join(parent_dir, subfolder, item)
    filesOrFolders = os.listdir(path)
    return filesOrFolders


def get_total_clockshark_hours():
    return ClockSharkTimeEntry.objects.all().aggregate(total=Sum("hours"))


def send_safety_inspection_email(inspection, user):
    unsatisfactory_items = inspection.get_unsatisfactory_items()
    comments = inspection.comments
    score = inspection.safety_score()

    # ✅ Only send if there are issues or comments
    if not unsatisfactory_items and not comments:
        return

    subject = f"⚠️ Safety Inspection Alert – Job {inspection.job.job_number}"

    body_lines = [
        f"Job: {inspection.job.job_number} – {inspection.job.job_name}",
        f"Inspection Date: {inspection.inspection_date}",
        f"Inspector: {inspection.inspector}",
        "",
        f"Safety Score: {score if score is not None else 'N/A'}%",
        "",
    ]

    if unsatisfactory_items:
        body_lines.append("UNSATISFACTORY ITEMS:")
        for item in unsatisfactory_items:
            body_lines.append(f" - {item}")
        body_lines.append("")

    if comments:
        body_lines.append("COMMENTS:")
        body_lines.append(comments)

    email_body = "\n".join(body_lines)

    # =========================
    # RECIPIENTS
    # =========================
    recipients = {
        "joe@gerloffpainting.com",
        "victor@gerloffpainting.com", "bridgette@gerloffpainting.com", "skip@gerloffpainting.com"
    }
    # recipients = {
    #     "joe@gerloffpainting.com",
    # }


    # ✅ Add superintendent if assigned and has an email
    superintendent = getattr(inspection.job, "superintendent", None)
    if superintendent and superintendent.email:
        recipients.add(superintendent.email)

    Email.sendEmail(
        subject,
        email_body,
        list(recipients),  # convert set → list
        False
    )

    JobNotes.objects.create(job_number=inspection.job,
                            note="Safety Inspection: " + email_body,
                            type="auto_misc_note", user=Employees.objects.get(user=user), date=date.today())

def get_client_ip(request):
    # Try X-Forwarded-For first
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # Take the first IP and strip whitespace/newlines
        ip = xff.split(",")[0].strip()
        if ip:
            return ip

    # Fallback to REMOTE_ADDR
    return request.META.get("REMOTE_ADDR")


def is_internal_ip(ip):
    internal_net = ipaddress.ip_network("192.168.168.0/24")
    return ipaddress.ip_address(ip) in internal_net