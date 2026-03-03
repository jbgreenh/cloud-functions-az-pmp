### scorecard

this script performs the monthly scorecard update on the 12th at 9:30AM

to deploy:

```bash
gcloud run jobs deploy scorecard \
 --source . \
 --memory 1Gi \
 --max-retries 5 \
 --region=us-west1 \
 --set-secrets=SENDGRID_API_KEY=projects/423748121399/secrets/sendgrid_api_key:latest,DISPENSATIONS_47_FOLDER=projects/423748121399/secrets/dispensations_47:latest,PATIENT_REQUESTS_FOLDER=projects/423748121399/secrets/patient_requests_folder:latest,SCORECARD_FILE=projects/423748121399/secrets/scorecard_file:latest,DATA_EMAIL=projects/423748121399/secrets/data_email:latest

```
