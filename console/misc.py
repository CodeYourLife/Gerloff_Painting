
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import os.path
from django.conf import settings
class Email:
    def sendEmail(title, body, to, filename):
        msg = MIMEMultipart()
        # sender = to
        sender = 'joe@gerloffpainting.com'
        msg['From'] = 'operations@gerloffpainting.com'
        msg['To'] = ", ".join(to)
        # msg['To'] = 'joe@gerloffpainting.com; taroli757@gmail.com'
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        if filename != False:
            with open(filename, 'rb') as file:
                attach = MIMEApplication(file.read(), _subtype='pdf')
                attach.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attach)
        text = msg.as_string()
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()


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

