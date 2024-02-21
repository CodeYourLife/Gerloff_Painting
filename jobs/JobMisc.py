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
    statusnote = ""
    job.start_date_checked = date.today()
    if status == 1:
        job.is_active = True
        statusnote = "Changed Status to Active"
    if status == 2:
        job.is_active = False
        statusnote = "Changed Status to Inactive"
    if did_date_change == True:
        job.start_date = newdate

        JobNotes.objects.create(job_number=job,
                                note="Start Date Changed to " + newdate + ". " + note + ". " + statusnote,
                                type="auto_start_date_note", user=author, date=date.today())
        if notify == True:
            recipients = ["joe@gerloffpainting.com"]
            if job.superintendent:
                if job.superintendent.email:
                    recipients.append(job.superintendent.email)
                else:
                    recipients.append("victor@gerloffpainting.com")
            else:
                recipients.append("victor@gerloffpainting.com")
            email_body = "Start Date For " + job.job_number + " - " + job.job_name + " changed to " + newdate + ". " + note + ". " + statusnote + ". By " + str(author)

            Email.sendEmail("Job Info Changed", email_body, recipients, False)
    else:
        JobNotes.objects.create(job_number=job, note=statusnote + ". " + note,
                                type="auto_start_date_note", user=author, date=date.today())
        if notify == True:
            recipients = ["joe@gerloffpainting.com"]
            if job.superintendent:
                if job.superintendent.email:
                    recipients.append(job.superintendent.email)
                else:
                    recipients.append("victor@gerloffpainting.com")
            else:
                recipients.append("victor@gerloffpainting.com")
            email_body = "Status changed for " + job.job_number + " - " + job.job_name + ". " + statusnote + ". " + note + ". By " + author
            Email.sendEmail("Job Info Changed", email_body, recipients, False)
    job.save()


def gerloff_super_change(job, superintendent, author):
    JobNotes.objects.create(job_number=job, note="Superintendent " + str(superintendent) + " Assigned to " + str(job),
                            type="auto_misc_note",
                            user=author, date=date.today())
    job.superintendent = superintendent
    email_body = str(superintendent) + "\n You have been assigned to \n" + str(job.job_number) + "\n" + str(
        job) + "\n" + str(job.client.company)
    Email.sendEmail("New Job - " + job.job_name, email_body, ['joe@gerloffpainting.com'], False)
    job.save()


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
