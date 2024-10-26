import warnings
import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from qtpy.QtCore import QObject, Signal
import msgpack

from haven import load_config


log = logging.getLogger(__name__)


class KafkaClient(QObject):
    run_started = Signal(str)
    run_updated = Signal(str)
    run_stopped = Signal(str)

    kafka_task = None

    def __init__(self, kafka_consumer: AIOKafkaConsumer = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._descriptors = {}
        self.kafka_consumer = kafka_consumer

    def start(self):
        # Make sure it's not already started
        if self.kafka_task is not None and not self.kafka_task.done():
            raise RuntimeError("Kafka client is already started.")
        # Start the client
        self.kafka_task = asyncio.ensure_future(self.consumer_loop())

    async def consumer_loop(self):
        # Create a kafka consumer if one was not provided
        if self.kafka_consumer is None:
            config = load_config()
            self.kafka_consumer = AIOKafkaConsumer(
                config['queueserver']['kafka_topic'],
                bootstrap_servers='fedorov.xray.aps.anl.gov:9092',
                group_id="my-group",
                value_deserializer=msgpack.loads,
            )
        consumer = self.kafka_consumer
        # Get cluster layout and join group `my-group`
        await consumer.start()
        try:
            # Consume events from the queueserver
            async for doc_type, doc in consumer:
                self._process_document(doc_type, doc)
        except Exception as ex:
            log.exception(ex)
            raise
        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()

    def _descriptor_to_run_uid(self, descriptor_uid):
        descriptor = self._descriptors[descriptor_uid]
        run_uid = descriptor['run_start']
        return run_uid

    def _drop_descriptors(self, run_uid: str):
        self._descriptors = {
            uid: doc for uid, doc in self._descriptors.items()
            if doc['run_start'] != run_uid
        }
  
    def _process_document(self, doc_type, doc):
        if doc_type == "start":
            # Notify clients that a new run has started
            uid = doc.get('uid', "")
            log.info(f"Received new start UID: {uid}")
            self.run_started.emit(uid)
        elif doc_type == "descriptor":
            # Save the description to reference to later
            self._descriptors[doc['uid']] = doc
        elif doc_type == "event":
            # Notify clients that this run has a new event
            descriptor_uid = doc.get('descriptor', "")
            run_uid = self._descriptor_to_run_uid(descriptor_uid)
            self.run_updated.emit(run_uid)
        elif doc_type == "stop":
            run_uid = doc['run_start']
            self._drop_descriptors(run_uid)
            self.run_stopped.emit(run_uid)
        else:
            warnings.warn(f"Unknown document type '{doc_type}'")
