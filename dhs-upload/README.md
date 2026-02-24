### dhs-upload

this script performs the weekly dhs-upload on tuesdays at 9:30AM

to deploy:

```bash
gcloud run jobs deploy dhs-upload \
 --source . \
 --memory 1Gi \
 --max-retries 5 \
 --region=us-west1 \
 --set-secrets=SENDGRID_API_KEY=projects/423748121399/secrets/sendgrid_api_key:latest,STANDARD_EXTRACT_FOLDER=projects/423748121399/secrets/standard_extract_folder:latest,SERVU_HOST=projects/423748121399/secrets/servu_host:latest,SERVU_PASSWORD=projects/423748121399/secrets/servu_password:latest,SERVU_PORT=projects/423748121399/secrets/servu_port:latest,SERVU_USERNAME=projects/423748121399/secrets/servu_username:latest

```
