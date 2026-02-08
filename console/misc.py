
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
import shutil
import fnmatch
import pythoncom
import winshell


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
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        candidate = xff.split(",")[0].strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass  # not a real IP, ignore it

    return request.META.get("REMOTE_ADDR")


def is_internal_ip(ip):

    # 🔹 DEV / TEST OVERRIDE
    if getattr(settings, "FORCE_INTERNAL_REQUESTS", False):
        return True

    ip_obj = ipaddress.ip_address(ip)

    # IPv4 internal network
    if ip_obj.version == 4:
        return ip_obj in ipaddress.ip_network("192.168.168.0/24")

    # IPv6 link-local addresses are always internal
    if ip_obj.version == 6 and ip_obj.is_link_local:
        return True

    return False

def create_excel_from_template(
    template_name,
    destination_subfolder,
    new_filename
):
    # Base media directory
    media_root = settings.MEDIA_ROOT

    # Where templates live
    template_folder = os.path.join(media_root, "excel_templates")
    template_path = os.path.join(template_folder, template_name)

    # Where the new file should go
    destination_folder = os.path.join(media_root, destination_subfolder)
    os.makedirs(destination_folder, exist_ok=True)

    destination_path = os.path.join(destination_folder, new_filename)

    # Copy template → new file
    shutil.copy(template_path, destination_path)

    return destination_path


def get_subfolders(base_path):
    if not os.path.isdir(base_path):
        return []

    return [
        {
            "name": folder,
            "path": os.path.join(base_path, folder),
        }
        for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
    ]

def find_post_bid_docs_shortcut(plans_folder):
    """
    Returns the full path to the first shortcut that matches '*Post Bid Docs*.lnk'
    """
    if not os.path.isdir(plans_folder):
        return None

    for name in os.listdir(plans_folder):
        # case-insensitive match for Post Bid Docs shortcut
        if fnmatch.fnmatch(name.lower(), "*post bid docs*.lnk"):
            return os.path.join(plans_folder, name)

    return None

def resolve_shortcut(lnk_path):
    """
    Resolve a Windows .lnk file to its target path.
    Safe for Django / Apache threads.
    """
    pythoncom.CoInitialize()
    try:
        return winshell.shortcut(lnk_path).path
    finally:
        pythoncom.CoUninitialize()

def create_folder_shortcut(target_folder, shortcut_dir):
    """
    Creates a Windows shortcut (.lnk) to target_folder
    inside shortcut_dir.
    """
    pythoncom.CoInitialize()
    try:
        # Ensure destination exists
        os.makedirs(shortcut_dir, exist_ok=True)

        folder_name = os.path.basename(os.path.normpath(target_folder))
        shortcut_path = os.path.join(shortcut_dir, f"{folder_name}.lnk")

        with winshell.shortcut(shortcut_path) as link:
            link.path = target_folder
            link.working_directory = target_folder
            link.description = f"Shortcut to {folder_name}"

        return shortcut_path
    finally:
        pythoncom.CoUninitialize()

def create_changeorder_shortcut_in_plan_folder(
    plan_folder,
    changeorder_folder,
    changeorder_id
):
    shortcut_name = f"Change Order {changeorder_id}.lnk"
    shortcut_path = os.path.join(plan_folder, shortcut_name)

    if os.path.exists(shortcut_path):
        return  # already exists, skip

    pythoncom.CoInitialize()
    try:
        with winshell.shortcut(shortcut_path) as link:
            link.path = changeorder_folder
            link.working_directory = changeorder_folder
            link.description = f"Change Order {changeorder_id}"
    finally:
        pythoncom.CoUninitialize()
