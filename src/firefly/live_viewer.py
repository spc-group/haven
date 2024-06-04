import logging
from aiokafka import AIOKafkaConsumer
import asyncio
import msgpack

from haven import load_config
from firefly.application import FireflyApplication
from firefly.run_viewer import RunViewerDisplayBase, cancellable


log = logging.getLogger(__name__)


class LiveViewerDisplay(RunViewerDisplayBase):
    start_uid: str = ""
    def __init__(self, kafka_consumer: AIOKafkaConsumer = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kafka_consumer = kafka_consumer
        self.db_task(self.start_kafka_consumer(), name="start_kafka_consumer")

    @cancellable
    async def start_kafka_consumer(self):
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
            async for msg in consumer:
                doc_type, doc = msg.value
                if doc_type == "start":
                    # Save the start UID to plot later
                    self.start_uid = doc.get('uid', "")
                    log.info(f"Found new start UID: {self.start_uid}")
                elif doc_type == "event":
                    # Update the plots and widgets with fresh data
                    try:
                        await self.update_live_run()
                    except Exception as ex:
                        log.exception(ex)
                        continue
        except Exception as ex:
            log.exception(ex)
            raise
        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()

    @cancellable
    async def update_live_run(self):
        # Make sure a start document was received
        if self.start_uid == "":
            return
        # Get updated run data from the database
        uids = [self.start_uid]
        task = self.db_task(self.db.load_selected_runs(uids), "update selected runs")
        await task
        # Update the plots and UI elements
        coros = asyncio.gather(
            self.update_1d_signals(),
            self.update_2d_signals(),
            self.update_metadata(),
            self.update_1d_plot(),
            self.update_2d_plot(),
            self.update_multi_plot(),
        )
        await coros
