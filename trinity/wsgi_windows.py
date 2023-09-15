activate_this = 'C:/Users/Administrator/Envs/trinity/Scripts/activate_this.py'
exec(open(activate_this).read(),dict(__file__=activate_this))

import os
import sys
import site

site.addsitedir('C:/Users/Administrator/Envs/trinity/Lib/site-packages')




sys.path.append('D:/Gerloff_Painting')
sys.path.append('D:/Gerloff_Painting/trinity')

os.environ['DJANGO_SETTINGS_MODULE'] = 'trinity.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trinity.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()