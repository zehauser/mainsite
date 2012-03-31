import logging
import pyodbc
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from aspc.coursesearch.tasks import update_catalog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Imports course data from the JICSWS server provided by ITS'

    def handle(self, *args, **options):
        logger.info("Starting full catalog update")
        logger.info("Connecting to {0}".format(settings.COURSE_DATA_DB['HOST']))
        update_catalog.delay()
        update_catalog.wait()
        logger.info("Full catalog update finished")