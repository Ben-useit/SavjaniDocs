from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from task_manager.classes import CeleryQueue
#from task_manager.workers import worker_medium

queue_sapitwa_uploads = CeleryQueue(
    name='sapitwa', label=_('Sapitwa Task') #, worker=worker_medium
)
queue_sapitwa_uploads.add_task_type(
    name='sapitwa.tasks.task_post_upload_process',
    label=_('Sapitwa: Process Uploaded Document')
)
queue_sapitwa_uploads.add_task_type(
    name='sapitwa.tasks.task_post_web_upload_process',
    label=_('Sapitwa: Process Uploaded Document')
)
