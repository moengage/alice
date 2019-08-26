# from __future__ import absolute_import, unicode_literals
# from celery import current_app
# from celery.bin import worker
#
# application = current_app._get_current_object()
# worker = worker.worker(app=application)
#
#
# options = {
#    'broker': 'redis://localhost:6379/0',
#    'loglevel': 'INFO',
#    'traceback': True,
#    'results': 'redis://localhost:6379/0',
#    'transport': 'redis://localhost:6379/0',
# }
# worker.run(**options)

from __future__ import absolute_import, unicode_literals
from alice.__init__ import app

from celery import current_app
from celery.bin import worker

application = current_app._get_current_object()

worker = worker.worker(app=application)

options = {
    'broker': app.config['CELERY_BROKER_URL'],
    'loglevel': 'INFO',
    'traceback': True,
}

worker.run(**options)