
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import os.path
from django.conf import settings
class Email:
    def sendEmail(title, body, to, filename):
        print(to)
        msg = MIMEMultipart()
        # sender = to
        sender = 'joe@gerloffpainting.com'
        msg['From'] = 'joe@gerloffpainting.com'
        msg['To'] = ", ".join(to)
        # msg['To'] = 'joe@gerloffpainting.com; taroli757@gmail.com'
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
        print("TESTING")
        print(filename)
        if filename != False:
            print("THIS WORKED")
            with open(filename, 'rb') as file:
                print("NOW I AM HERE")
                attach = MIMEApplication(file.read(), _subtype='pdf')
                attach.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attach)
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()
        #here is the command you will put in your actual cod
        #Email.sendEmail("New Job - " + job.job_name, email_body, 'joe@gerloffpainting.com')


def createfolder(subfolder):
        print("RAN THIS HERE. Subfolder = " + subfolder)
        parent_dir = settings.MEDIA_ROOT
        path = os.path.join(parent_dir, subfolder)
        try:
            os.mkdir(path)
        except OSError as error:
            print(error)

def openfolder(subfolder, item):
    parent_dir = settings.MEDIA_ROOT
    path = os.path.join(parent_dir, subfolder)
    path = path + "/" + str(item)
    path = os.path.realpath(path)
    os.startfile(path)

