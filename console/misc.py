
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import os.path
from django.conf import settings
class Email:
    def sendEmail(title, body, to):
        msg = MIMEMultipart()
        sender = to
        msg['From'] = 'joe@gerloffpainting.com'
        msg['To'] = to
        # msg['To'] = 'joe@gerloffpainting.com; taroli757@gmail.com'
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        text = msg.as_string()
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


