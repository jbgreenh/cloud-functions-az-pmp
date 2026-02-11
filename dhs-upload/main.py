import logging
import os
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from zoneinfo import ZoneInfo

import functions_framework
import google.auth
import paramiko
from az_pmp_utils import drive
from googleapiclient.discovery import build
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

MAX_SERVU_FILE_COUNT = 5                # the max number of files to keep on the servu
PHX_TZ = ZoneInfo('America/Phoenix')    # phoenix timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_string = StringIO()
stream_handler = logging.StreamHandler(stream=stream_string)
logger.addHandler(stream_handler)


def get_last_sunday() -> date:
    """
    gets the date of the last sunday

    returns:
        a datetime.date for the last sunday
    """
    today = datetime.now(tz=PHX_TZ).date()
    days_since_sunday = today.weekday() + 1
    return today - timedelta(days=days_since_sunday)


def remove_oldest_file(sftp: paramiko.SFTPClient) -> None:
    """
    removes the oldest file from the current folder in the sftp; maintains the `MAX_SERVU_FILE_COUNT` on the server

    args:
        sftp: paramiko SFTPClient
    """
    files = sftp.listdir_attr()
    if len(files) > MAX_SERVU_FILE_COUNT:
        oldest_file = min(files, key=lambda f: f.st_mtime)  # type: ignore[reportArgumentType] | these files will have st_mtime
        logger.info('removing oldest file: %s...', oldest_file.filename)
        sftp.remove(oldest_file.filename)
        logger.info('file removed')
    else:
        logger.warning('%s files on servu, none removed', MAX_SERVU_FILE_COUNT)


def upload_latest_dhs_file(sftp: paramiko.SFTPClient, folder: str) -> None:
    """
    uploads the latest standard extract to the DHS sftp

    args:
        sftp: paramiko SFTPClient connected to the DHS sftp
        folder: the google drive folder for the standard extracts
    """
    last_sunday = get_last_sunday()
    file_name = last_sunday.strftime('AZ_%Y%m%d.csv')
    files = sftp.listdir()

    if file_name not in files:
        logger.info('%s not found, uploading...', file_name)
        creds, _proj_id = google.auth.default()
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        extract = drive.lazyframe_from_file_name(file_name=file_name, folder_id=folder, drive_ft='csv', service=service, separator='|', infer_schema=False)
        csv_buffer = BytesIO()
        extract.collect().write_csv(csv_buffer, separator='|')
        csv_buffer.seek(0)
        logger.info('writing %s to sftp...', file_name)
        sftp.putfo(csv_buffer, remotepath=file_name)
        logger.info('file uploaded')
    else:
        logger.warning('%s found, no upload yet', file_name)


@functions_framework.http
def main(request):
    folder = os.environ['STANDARD_EXTRACT_FOLDER']

    sftp_host = os.environ['SERVU_HOST']
    sftp_port = os.environ['SERVU_PORT']
    sftp_user = os.environ['SERVU_USERNAME']
    sftp_password = os.environ['SERVU_PASSWORD']

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=sftp_host, port=int(sftp_port), username=sftp_user, password=sftp_password)
    sftp = ssh.open_sftp()

    try:
        upload_latest_dhs_file(sftp, folder)
        remove_oldest_file(sftp)
    finally:
        sftp.close()
        ssh.close()

        message = Mail(
            from_email='pmpdata@azpharmacy.gov',
            to_emails=['pmpdata@azpharmacy.gov'],
            subject='pmp-analytics cloud function log: dhs_upload',
            html_content=stream_string.getvalue(),
        )

        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        _response = sg.send(message)
