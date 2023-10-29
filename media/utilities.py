from django.core.files.storage import FileSystemStorage
import os
import os.path
import csv
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse

class MediaUtilities(object):

    def __init__(self):
        super(MediaUtilities, self).__init__()
    def getDirectoryContents(self, id, value,app):
        file_path = os.path.join(settings.MEDIA_ROOT, app, str(id), os.path.basename(value))
        if os.path.exists(file_path):
            name = value.split('.')[0]
            mimetype = value.split('.')[1]
            with open(file_path, 'rb') as fh:
                return HttpResponse(fh.read(), headers={'Content-Type': f'image/{mimetype}','Content-Disposition': f'attachment; filename="{name}.{mimetype}"'})