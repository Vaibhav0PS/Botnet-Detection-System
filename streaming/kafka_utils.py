import json


def json_serializer(value):
    return json.dumps(value, default=str).encode("utf-8")


def json_deserializer(value):
    return json.loads(value.decode("utf-8"))


def create_producer(bootstrap_servers):
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=json_serializer,
        key_serializer=lambda value: value.encode("utf-8") if value else None,
    )


def create_consumer(topic, bootstrap_servers, group_id, auto_offset_reset="latest"):
    from kafka import KafkaConsumer

    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=True,
        value_deserializer=json_deserializer,
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
    )

