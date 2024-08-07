
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
        print("HERE3")
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()
        print("HERE4")

    def sendEmail2(title, body, to, filename):
        msg = MIMEMultipart()
        # sender = to
        sender = 'joe@gerloffpainting.com'
        msg['From'] = 'operations@gerloffpainting.com'
        msg['To'] = ", ".join(to)
        msg['Subject'] = title
        msg.attach(MIMEText(body, 'plain'))
        print(filename)
        for f in filename:
            print("Lets go")
            print(f)
            att_name = os.path.basename(f)
            with open(f, 'rb') as file:
                attach = MIMEApplication(file.read(), _subtype='pdf')
                attach.add_header('Content-Disposition', 'attachment', filename=att_name)
                # attach.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attach)
        text = msg.as_string()
        print("HERE3")
        s = smtplib.SMTP('remote.gerloffpainting.com')
        s.sendmail(sender, to, text)
        s.quit()
        print("HERE4")
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


