# sftp-backup

this script performs the daily sftp-backups at 8:30AM

to deploy:

```bash
gcloud run jobs deploy sftp-backup \
 --source . \
 --memory 3Gi \
 --max-retries 5 \
 --region=us-west1 \
 --set-secrets=SENDGRID_API_KEY=projects/423748121399/secrets/sendgrid_api_key:latest,DATA_EMAIL=projects/423748121399/secrets/data_email:latest,\
SFTP_HOST=projects/423748121399/secrets/bamboo_sftp_host:latest,SFTP_PORT=projects/423748121399/secrets/bamboo_sftp_port:latest,\
SFTP_USERNAME=projects/423748121399/secrets/bamboo_sftp_username:latest,SFTP_PASSWORD=projects/423748121399/secrets/bamboo_sftp_password:latest,\
SFTP_REMOTE_PATH=projects/423748121399/secrets/bamboo_sftp_remote_path:latest,PMP_SFTP_HOST=projects/423748121399/secrets/pmp_sftp_host:latest,\
PMP_SFTP_PORT=projects/423748121399/secrets/pmp_sftp_port:latest,PMP_SFTP_USERNAME=projects/423748121399/secrets/pmp_sftp_username:latest,\
PMP_SFTP_PASSWORD=projects/423748121399/secrets/pmp_password:latest,PMP_SFTP_REMOTE_PATH=projects/423748121399/secrets/pmp_sftp_remote_path:latest,\
SFTP_BACKUP_FOLDER=projects/423748121399/secrets/folders_sftp_backup:latest,PMP_SFTP_BACKUP_FOLDER=projects/423748121399/secrets/folder_pmp_sftp_backup:latest

```
