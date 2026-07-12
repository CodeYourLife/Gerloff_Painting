import console.misc
from jobs.models import *
from employees.models import *
from console.misc import Email
from datetime import date
from django.contrib.auth.models import User
import webbrowser
import dropbox
from dropbox.exceptions import AuthError
import base64
import requests
import json

def start_date_change(job, newdate, status, note, author, did_date_change, notify):
    # status is 1- active, 2- not active, 3 - no change
    success=False
    statusnote = ""
    sender = (author.email or "").strip() if author else ""
    if not sender:
        sender = "bridgette@gerloffpainting.com"

    recipients = []
    if job.superintendent and job.superintendent.email:
        recipients.append(job.superintendent.email)

    if did_date_change:
        job.start_date_checked = date.today()
    if status == 1:
        job.is_active = True
        statusnote = "Changed Status to Active"
    if status == 2:
        job.is_active = False
        statusnote = "Changed Status to Inactive"
    if did_date_change == True:
        job.start_date = newdate
        job.is_start_date_guessed = False

        JobNotes.objects.create(job_number=job,
                                note="Start Date Changed to " + newdate + ". " + note + ". " + statusnote,
                                type="auto_start_date_note", user=author, date=date.today())
        if notify == True:
            email_body = "Start Date For " + job.job_number + " - " + job.job_name + " changed to " + newdate + ". " + note + ". " + statusnote + ". By " + str(author)
            try:
                if recipients:
                    Email.sendEmail("Job Info Changed", email_body, recipients, False, sender)
                    success=True
            except:
                success=False
    else:
        JobNotes.objects.create(job_number=job, note=statusnote + ". " + note,
                                type="auto_start_date_note", user=author, date=date.today())
        if notify == True:
            email_body = "Status changed for " + job.job_number + " - " + job.job_name + ". " + statusnote + ". " + note + ". By " + str(author)
            try:
                if recipients:
                    Email.sendEmail("Job Info Changed", email_body, recipients, False, sender)
                    success=True
            except:
                success=False
    job.save()
    return success


def gerloff_super_change(job, superintendent, author):
    JobNotes.objects.create(
        job_number=job,
        note="Superintendent " + str(superintendent) + " Assigned to " + str(job),
        type="auto_misc_note",
        user=author,
        date=date.today()
    )

    job.superintendent = superintendent
    job.save()

    author_email = (author.email or "").strip()
    superintendent_email = (superintendent.email or "").strip()

    recipients = []

    if author_email:
        recipients.append(author_email)

    if superintendent_email:
        recipients.append(superintendent_email)

    if author_email:
        sender = author_email
    else:
        sender = "bridgette@gerloffpainting.com"

    main_email_sent = False
    management_email_sent = False

    # ----------------------------
    # Email to superintendent/author
    # ----------------------------
    if recipients:
        email_body = (
            str(superintendent)
            + "\n\nYou have been assigned to:"
            + "\n"
            + str(job.job_number)
            + "\n"
            + str(job)
            + "\n"
            + str(job.client.company)
        )

        try:
            Email.sendEmail(
                "New Job - " + job.job_name,
                email_body,
                recipients,
                False,
                sender
            )
            main_email_sent = True
        except Exception as e:
            return {
                "email_sent": False,
                "email_message": "Email failed to send: " + str(e)
            }

    # ----------------------------
    # Email to Bridgette/Admin2
    # ----------------------------
    management_email_body = (
        "Superintendent "
        + str(superintendent)
        + " has been assigned to job "
        + str(job.job_number)
        + " - "
        + str(job.job_name)
        + ". Please update management console."
    )

    try:
        Email.sendEmail(
            "Management Console Update Needed - " + job.job_number,
            management_email_body,
            [
                "bridgette@gerloffpainting.com",
                "admin2@gerloffpainting.com",
                "joe@gerloffpainting.com"
            ],
            False,
            sender
        )
        management_email_sent = True

    except Exception as e:
        return {
            "email_sent": main_email_sent,
            "email_message": (
                "Superintendent was changed, but the management console email failed to send: "
                + str(e)
            )
        }

    # ----------------------------
    # User-facing message
    # ----------------------------
    if author_email and superintendent_email:
        email_message = "Email sent to you and the superintendent. Management console email was also sent."

    elif author_email and not superintendent_email:
        email_message = (
            "Superintendent does not have an email on file. "
            "Email was sent to you only. Management console email was also sent."
        )

    elif not author_email and superintendent_email:
        email_message = (
            "You do not have an email on file. "
            "Email was sent to superintendent using Bridgette as the sender. "
            "Management console email was also sent."
        )

    else:
        email_message = (
            "Neither you nor the superintendent has an email on file. "
            "Only the management console email was sent."
        )

    return {
        "email_sent": main_email_sent or management_email_sent,
        "email_message": email_message
    }


def gerloff_estimator_pm_change(job, estimator, project_manager, author):
    changes = []

    if job.estimator_id != estimator.id:
        changes.append(("Estimator", estimator))

    if job.project_manager_id != project_manager.id:
        changes.append(("Project Manager", project_manager))

    if not changes:
        return {
            "email_sent": False,
            "email_message": "No assignments changed."
        }

    for role, employee in changes:
        JobNotes.objects.create(
            job_number=job,
            note=role + " " + str(employee) + " Assigned to " + str(job),
            type="auto_misc_note",
            user=author,
            date=date.today()
        )

    job.estimator = estimator
    job.project_manager = project_manager
    job.save()

    author_email = (author.email or "").strip()
    sender = author_email or "bridgette@gerloffpainting.com"
    main_email_sent = False
    management_email_sent = False
    missing_email_names = []
    failed_email_messages = []

    assignments_by_employee = {}
    for role, employee in changes:
        assignments_by_employee.setdefault(employee.id, {
            "employee": employee,
            "roles": []
        })
        assignments_by_employee[employee.id]["roles"].append(role)

    for assignment in assignments_by_employee.values():
        employee = assignment["employee"]
        employee_email = (employee.email or "").strip()
        roles_text = " and ".join(assignment["roles"])

        if not employee_email:
            missing_email_names.append(str(employee))
            continue

        email_body = (
            str(employee)
            + "\n\nYou have been assigned as "
            + roles_text
            + " to:"
            + "\n"
            + str(job.job_number)
            + "\n"
            + str(job)
            + "\n"
            + str(job.client.company)
        )

        try:
            Email.sendEmail(
                "New Job - " + job.job_name,
                email_body,
                [employee_email],
                False,
                sender
            )
            main_email_sent = True
        except Exception as e:
            failed_email_messages.append(str(employee) + ": " + str(e))

    management_lines = []
    for role, employee in changes:
        management_lines.append(role + " " + str(employee))

    management_email_body = (
        ", ".join(management_lines)
        + " assigned to job "
        + str(job.job_number)
        + " - "
        + str(job.job_name)
        + ". Please update management console."
    )

    try:
        Email.sendEmail(
            "Management Console Update Needed - " + job.job_number,
            management_email_body,
            [
                "bridgette@gerloffpainting.com",
                "admin2@gerloffpainting.com",
                "joe@gerloffpainting.com"
            ],
            False,
            sender
        )
        management_email_sent = True
    except Exception as e:
        return {
            "email_sent": main_email_sent,
            "email_message": (
                "Assignments were changed, but the management console email failed to send: "
                + str(e)
            )
        }

    email_message = "Assignment updated. Management console email was sent."
    if main_email_sent:
        email_message += " Assignment email was sent."
    if missing_email_names:
        email_message += " No email on file for: " + ", ".join(missing_email_names) + "."
    if failed_email_messages:
        email_message += " Some assignment emails failed: " + "; ".join(failed_email_messages) + "."

    return {
        "email_sent": main_email_sent or management_email_sent,
        "email_message": email_message
    }


def open_dropbox(jobnumber, user):
    job = Jobs.objects.get(job_number=jobnumber)
    query = str(job.job_number) + " " + str(job.job_name)
    # dbx = dropbox.Dropbox(
    #     '0ZO2RCS5HXUAAAAAAAAAAYnYkAqko1APtMIdkSLShC9Hn650xeuxoYe3wtgQvh7I')
    dbx = dropbox.Dropbox(
        app_key= 'kl6kuitmi3x0ol8',
          app_secret = 'vax8zqlgvdwoc47',
                         oauth2_refresh_token = '0ZO2RCS5HXUAAAAAAAAAAYnYkAqko1APtMIdkSLShC9Hn650xeuxoYe3wtgQvh7I'
    )

    # try:
    #     shared_link_metadata = dbx.sharing_create_shared_link_with_settings("/Gerloff Painting/Steve/D3130 Convert X132 for MSC Consolidation")
    # except:
    #     shared_link_metadata = dbx.sharing_list_shared_links("/Gerloff Painting/Steve/D3130 Convert X132 for MSC Consolidation", cursor=None, direct_only=None)
    # for link in shared_link_metadata.links:
    #     print(link.url)
    try:
        x = False
        while x == False:
            for entry in dbx.files_list_folder("/Gerloff Painting/").entries:
                try:
                    # print(entry.name)
                    for entry2 in dbx.files_list_folder("/Gerloff Painting/" + entry.name).entries:
                        if entry2.name == query:
                            # print("------------FOUND IT")
                            try:
                                shared_link_metadata = dbx.sharing_create_shared_link_with_settings(entry2.path_lower)
                                shared_link_metadata = dbx.sharing_list_shared_links(entry2.path_lower, cursor=None,
                                                                                     direct_only=None)
                            except:
                                shared_link_metadata = dbx.sharing_list_shared_links(entry2.path_lower, cursor=None,
                                                                                     direct_only=None)
                            for link in shared_link_metadata.links:
                                # print(link.url)
                                return link.url
                            x = True
                            break
                        # else:
                        #     print(entry2.name)
                except:
                    print(entry.name + " -Not a folder")
                if x == True:
                    break
            return False
            break
        #now
        # print(dbx.files_search_v2(query="D630A CRMC Vertical Expansion"))

        # x=1
        # for entry in dbx.files_list_folder("/Gerloff Painting/").entries:
        #     if entry.name == "Steve":
        #         print(entry.link)

        # shared_link_metadata = dbx.sharing_create_shared_link_with_settings("/Gerloff Painting/Steve/D3130 Convert X132 for MSC Consolidation")
        # print(shared_link_metadata)
        # print(shared_link_metadata.url)

        # existing_link_metadata = dbx.sharing_list_shared_links("/Gerloff Painting/Steve/D3130 Convert X132 for MSC Consolidation", cursor=None, direct_only=None)
        # for link in existing_link_metadata.links:
        #     print(link.url)

        # print(dbx.files_search_v2(query="D630A CRMC Vertical Expansion"))
    except Exception as e:
        print(str(e))

    # link="https://www.dropbox.com/work/" + folder + "/Gerloff Painting/"

    # webbrowser.open(link, new=2)

def dropbox2():
    APP_KEY = 'kl6kuitmi3x0ol8'
    url = f'https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&' \
          f'response_type=code&token_access_type=offline'

    webbrowser.open(url)

def dropbox3():
    APP_KEY = 'kl6kuitmi3x0ol8'
    APP_SECRET = 'vax8zqlgvdwoc47'
    ACCESS_CODE_GENERATED = 'u7GKhT_p-qIAAAAAAAAEWS4pykytwV7I_1SlOa_ratM'

    BASIC_AUTH = base64.b64encode(f'{APP_KEY}:{APP_SECRET}'.encode())

    headers = {
        'Authorization': f"Basic {BASIC_AUTH}",
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = f'code={ACCESS_CODE_GENERATED}&grant_type=authorization_code'

    response = requests.post('https://api.dropboxapi.com/oauth2/token',
                             data=data,
                             auth=(APP_KEY, APP_SECRET))
    print(json.dumps(json.loads(response.text), indent=2))
