from aiokafka import AIOKafkaConsumer
import asyncio

from haven import load_config
from .application import FireflyApplication
from .run_browser import RunBrowserDisplay


class LiveViewerDisplay(RunBrowserDisplay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # asyncio.ensure_future(self.prepare_kafka_client())
        self.db_task(self.start_kafka_client())

    async def start_kafka_client(self):
        config = load_config()
        consumer = AIOKafkaConsumer(
            config['queueserver']['kafka_topic'],
            bootstrap_servers='localhost:9092',
            group_id="my-group"
        )
        # Get cluster layout and join group `my-group`
        await consumer.start()
        try:
            # Consume messages
            async for msg in consumer:
                print("consumed: ", msg.topic, msg.partition, msg.offset,
                      msg.key, msg.value, msg.timestamp)
        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()
