import base64
import logging
from io import StringIO
from google.cloud import pubsub_v1

# global log stream; log_stream.getvalue() will have the results
log_stream = StringIO()
logging.basicConfig(stream=log_stream, level=logging.INFO)

def make_some_logs():
  logging.info('test 1')
  logging.error('test 2')
  logging.info('ok thats enough')

def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print(pubsub_message)

    make_some_logs()

    project_id = 'pmp-analytics'
    topic_id = 'email-logs'
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    data = log_stream.getvalue().encode('utf-8')
    future = publisher.publish(topic_path, data)
    print(future.result())
    print('published message')
