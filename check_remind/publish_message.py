from google.cloud import pubsub_v1
import secret_id
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './data-potential-365808-45ad793328a9.json'

# TODO(developer)
project_id = secret_id.project_id
topic_id = secret_id.topic_id


def publish_message(data_str):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    # Data must be a bytestring
    data = data_str.encode("utf-8")
    # Add two attributes, origin and username, to the message
    future = publisher.publish(
        topic_path, data, origin="python-sample", username="gcp"
    )
    print(future.result())
    print(f"Published messages with custom attributes to {topic_path}.")
