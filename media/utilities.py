from django.core.files.storage import FileSystemStorage
import os
import os.path
import csv
import mimetypes
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse

from changeorder.models import ChangeOrders

#------OLD DELETED 4.3.26
# class MediaUtilities(object):
#
#     def __init__(self):
#         super(MediaUtilities, self).__init__()
#     def getDirectoryContents(self, id, value,app):
#         if app=="changeorder":
#             changeorder=ChangeOrders.objects.get(id=id)
#             file_path = os.path.join(settings.MEDIA_ROOT, app, rf"{changeorder.job_number.job_number} COP #{changeorder.cop_number}", os.path.basename(value))
#         else:
#             file_path = os.path.join(settings.MEDIA_ROOT, app, str(id), os.path.basename(value))
#         if os.path.exists(file_path):
#             name = value.split('.')[0]
#             mimetype = value.split('.')[1]
#             if mimetype == "pdf":
#                 with open(file_path, 'rb') as fh:
#                     return HttpResponse(fh.read(), headers={'Content-Type': f'application/{mimetype}','Content-Disposition': f'inline'})
#
#             else:
#                 with open(file_path, 'rb') as fh:
#                     return HttpResponse(fh.read(), headers={'Content-Type': f'image/{mimetype}','Content-Disposition': f'inline; filename="{name}.{mimetype}"'})
#

import os
import mimetypes
from django.http import HttpResponse
from django.conf import settings

class MediaUtilities(object):

    def __init__(self):
        super(MediaUtilities, self).__init__()

    def getDirectoryContents(self, id, value, app):
        if app == "changeorder":
            changeorder = ChangeOrders.objects.get(id=id)
            file_path = os.path.join(
                settings.MEDIA_ROOT,
                app,
                rf"{changeorder.job_number.job_number} COP #{changeorder.cop_number}",
                os.path.basename(value)
            )
        else:
            file_path = os.path.join(
                settings.MEDIA_ROOT,
                app,
                str(id),
                os.path.basename(value)
            )

        if os.path.exists(file_path):
            filename = os.path.basename(value)
            content_type, _ = mimetypes.guess_type(file_path)

            if not content_type:
                content_type = "application/octet-stream"

            disposition = "inline"
            if not content_type.startswith("image/") and content_type != "application/pdf":
                disposition = f'attachment; filename="{filename}"'
            else:
                disposition = f'inline; filename="{filename}"'

            with open(file_path, 'rb') as fh:
                return HttpResponse(
                    fh.read(),
                    headers={
                        "Content-Type": content_type,
                        "Content-Disposition": disposition,
                    }
                )