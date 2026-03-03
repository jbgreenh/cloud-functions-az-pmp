import logging
import os
import stat
import sys
from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import google.auth
import paramiko
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

PHX_TZ = ZoneInfo('America/Phoenix')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_string = StringIO()
stream_handler = logging.StreamHandler(stream=stream_string)
logger.addHandler(stream_handler)


def upload_file(service, sftp: paramiko.SFTPClient, remote_file_path: str, drive_folder_id: str) -> None:  # noqa: ANN001 | service is dynamically typed
    """
    uploads a file to the google drive if it is new or has been modified
    only checks files with an mtime younger than 24 hours

    args:
       service: an authorized google service
       sftp: a connected paramiko SFTPClient
       remote_file_path: the remote file path to the file for potential uploading
       drive_folder_id: the id of the target folder on the google drive
    """
    remote_file = os.path.basename(remote_file_path)  # noqa: PTH119 | paramiko is not compatible with Path

    st_mtime = sftp.lstat(remote_file_path).st_mtime
    remote_file_mtime = datetime.fromtimestamp(float(st_mtime)).astimezone(tz=ZoneInfo('UTC')) if isinstance(st_mtime, int) else datetime(year=2001, month=1, day=1, tzinfo=ZoneInfo('UTC'))

    if (datetime.now(tz=ZoneInfo('UTC')) - remote_file_mtime) <= timedelta(hours=24):
        try:
            results = service.files().list(q=f"name = '{remote_file}' and '{drive_folder_id}' in parents",
                                        supportsAllDrives=True,
                                        includeItemsFromAllDrives=True,
                                        fields='files(id, modifiedTime)').execute()
            files = results.get('files', [])
            if files:
                logger.debug('%s already exists on google drive', remote_file)
                drive_file_id = files[0]['id']
                drive_file_modified_time = datetime.fromisoformat(files[0]['modifiedTime'])
                if remote_file_mtime > drive_file_modified_time:
                    logger.debug('%s has been updated since uploading', remote_file)
                    logger.debug('updating %s on google drive...', remote_file)
                    with sftp.file(remote_file_path, 'rb') as remote_file_content:
                        remote_file_content.prefetch()
                        media = MediaIoBaseUpload(remote_file_content, mimetype='application/octet-stream', chunksize=1024 * 1024, resumable=True)
                        service.files().update(fileId=drive_file_id, media_body=media, supportsAllDrives=True).execute()
                        logger.info('%s updated on google drive.', remote_file)
                else:
                    logger.debug('%s has not been updated, skipping...', remote_file)
            else:
                logger.debug('uploading %s to google drive...', remote_file)
                with sftp.file(remote_file_path, 'rb') as remote_file_content:
                    remote_file_content.prefetch()
                    media = MediaIoBaseUpload(remote_file_content, mimetype='application/octet-stream', chunksize=1024 * 1024, resumable=True)
                    file_metadata = {
                        'name': remote_file,
                        'parents': [drive_folder_id],
                    }
                    service.files().create(supportsAllDrives=True, media_body=media, body=file_metadata).execute()
                    logger.info('%s uploaded to google drive.', remote_file)

        except HttpError:
            logger.exception('error checking google drive: ')
            sys.exit()
    else:
        logger.debug('%s is %s hours old, skipping...', remote_file, round((datetime.now(tz=ZoneInfo('UTC')) - remote_file_mtime).total_seconds() / 60 / 60, 2))


def find_or_create_folder(service, folder_name: str, parent_folder_id: str) -> str:  # noqa: ANN001 | service is dynamically typed
    """
    finds or creates the specified folder on the google drive

    args:
        service: an authorized google drive service
        folder_name: the folder name
        parent_folder_id: the id of the parent folder on the google drive

    returns:
        the folder id of the target folder
    """
    try:
        results = service.files().list(q=f"name = '{folder_name}' and '{parent_folder_id}' in parents",
                                       supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = results.get('files', [])
        if not files:
            file_metadata = {
                'name': folder_name,
                'parents': [parent_folder_id],
                'mimeType': 'application/vnd.google-apps.folder',
            }
            folder = service.files().create(supportsAllDrives=True, body=file_metadata).execute()
            return folder['id']
        return files[0]['id']

    except HttpError:
        logger.exception('error checking google drive: ')
        sys.exit()


def upload_directory(service, sftp: paramiko.SFTPClient, remote_path: str, drive_folder_id: str) -> None:  # noqa: ANN001 | service is dynamically typed
    """
    upload an entire directory from an sftp to the google drive as needed

    args:
        service: an authorized google drive service
        sftp: a connected paramiko SFTPClient
        remote_path: the remote path to the directory
        drive_folder_id: the id for the target google drive folder
    """
    sftp.chdir(remote_path)
    logger.debug('checking %s...', remote_path)
    for item in sftp.listdir():
        remote_item_path = remote_path + item
        mode = sftp.lstat(remote_item_path).st_mode
        if not isinstance(mode, int):
            logger.error('could not get mode for %s on sftp', remote_item_path)
            sys.exit()
        if stat.S_ISREG(mode):
            upload_file(service, sftp, remote_item_path, drive_folder_id)
        elif stat.S_ISDIR(mode):
            subfolder_name = item
            subfolder_drive_folder_id = find_or_create_folder(service, subfolder_name, drive_folder_id)
            upload_directory(service, sftp, remote_item_path + '/', subfolder_drive_folder_id)


if __name__ == '__main__':
    process_start = datetime.now(tz=PHX_TZ)
    logger.info('sftp backup start: %s\n', process_start)
    creds = google.auth.default()
    service = build('drive', 'v3', credentials=creds)

    sftp_types = ['pmp', 'vendor']
    for sftp_type in sftp_types:
        if sftp_type == 'vendor':
            sftp_host = os.environ['SFTP_HOST']
            sftp_port = os.environ['SFTP_PORT']
            sftp_user = os.environ['SFTP_USERNAME']
            sftp_password = os.environ['SFTP_PASSWORD']
            remote_path = os.environ['SFTP_REMOTE_PATH']

            drive_folder_id = os.environ['SFTP_BACKUP_FOLDER']
        else:
            sftp_host = os.environ['PMP_SFTP_HOST']
            sftp_port = os.environ['PMP_SFTP_PORT']
            sftp_user = os.environ['PMP_SFTP_USERNAME']
            sftp_password = os.environ['PMP_SFTP_PASSWORD']
            remote_path = os.environ['PMP_SFTP_REMOTE_PATH']

            drive_folder_id = os.environ['PMP_SFTP_BACKUP_FOLDER']

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=sftp_host, port=int(sftp_port), username=sftp_user, password=sftp_password)
        sftp = ssh.open_sftp()
        try:
            start_time = datetime.now(tz=PHX_TZ)
            logger.info('updating %s sftp backup: %s...\n', sftp_type, start_time)
            upload_directory(service, sftp, remote_path, drive_folder_id)
        finally:
            if sftp:
                sftp.close()
                logger.debug('sftp closed')
            if ssh:
                ssh.close()
                logger.debug('ssh closed')
            end_time = datetime.now(tz=PHX_TZ)
            logger.info('%s sftp backup complete: %s', sftp_type, end_time)

    process_end = datetime.now(tz=PHX_TZ)
    logger.info('sftp backup complete: %s\n', process_end)

    message = Mail(
        from_email=os.environ['DATA_EMAIL'],
        to_emails=[os.environ['DATA_EMAIL']],
        subject='pmp-analytics cloud function log: sftp-backup',
        plain_text_content=stream_string.getvalue(),
    )

    sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    _response = sg.send(message)
