import pandas as pd
from kafka import KafkaProducer
import json
import time
from datetime import datetime

KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'mock_l1_stream'


def load_data()->pd.DataFrame:
    df = pd.read_csv("l1_day.csv")
    return df

def create_kafka_producer():
    producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    return producer

def send_data(producer,df):
    for i in range(len(df)):
        message = {'id': df['ts_event'][i], 'publisher_id': str(df['publisher_id'][i]), 'ask_px_00': str(df['ask_px_00'][i]), 'ask_sz_00': str(df['ask_sz_00'][i])}
        # Send the message to the topic
        producer.send(KAFKA_TOPIC, message)
        print(f"Sent: {message}")
        time.sleep(0.001)
if __name__=="__main__":
    df = load_data()
    producer = create_kafka_producer()
    send_data(producer, df)
    producer.flush(1)