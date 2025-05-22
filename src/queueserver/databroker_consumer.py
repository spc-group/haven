import logging
import sys
from typing import Mapping, Sequence

import databroker
import msgpack
from bluesky_kafka import BlueskyConsumer

import haven

log = logging.getLogger(__name__)


class DatabrokerConsumer(BlueskyConsumer):
    """Send Bluesky documents received from a Kafka broker to a databroker catalog.

    There is no default configuration. A reasonable configuration for production is
        consumer_config={
            "auto.offset.reset": "latest"
        }

    Parameters
    ----------
    topic_catalog_map
      Translates Kafka topic names to Tiled catalogs. Each value
      should be the name of a catalog available directly under
      *tiled_client*.
    bootstrap_servers
        Kafka server addresses as strings such as
        ``["broker1:9092", "broker2:9092", "127.0.0.1:9092"]``
    group_id : str
        Required string identifier for the consumer's Kafka Consumer group.
    consumer_config : dict
        Override default configuration or specify additional configuration
        options to confluent_kafka.Consumer.
    polling_duration : float
        Time in seconds to wait for a message before running function work_during_wait
        in the _poll method. Default is 0.05.
    deserializer : function, optional
        Function to deserialize data. Default is msgpack.loads.

    """

    def __init__(
        self,
        topic_catalog_map: Mapping,
        bootstrap_servers: Sequence[str],
        group_id: str,
        consumer_config: Mapping | None = None,
        polling_duration: float | int = 0.05,
        deserializer=msgpack.loads,
    ):
        self.topic_catalog_map = topic_catalog_map
        # Create writers for each Tiled catalog
        catalog_names = set(topic_catalog_map.values())
        self.writers = {
            name: databroker.catalog[name].v1.insert for name in catalog_names
        }
        super().__init__(
            topics=list(topic_catalog_map.keys()),
            bootstrap_servers=",".join(bootstrap_servers),
            group_id=group_id,
            consumer_config=consumer_config,
            polling_duration=polling_duration,
            deserializer=deserializer,
        )

    def process_document(self, topic: str, name: str, doc: Mapping) -> bool:
        """Write the Bluesky document to the associated Tiled catalog.

        Parameters
        ----------
        topic
            the Kafka topic of the message containing name and doc
        name
            bluesky document name: `start`, `descriptor`, `event`, etc.
        doc
            bluesky document

        Returns
        -------
        continue_polling
            return False to break out of the polling loop, return True to continue polling
        """
        catalog = self.topic_catalog_map[topic]
        log.info(f"Writing {name} doc from {topic=} to {catalog=}.")
        writer = self.writers[catalog]
        writer(name, doc)


def main():
    """Launch the tiled consumer."""
    logging.basicConfig(level=logging.INFO)
    config = haven.load_config()
    bootstrap_servers = ["localhost:9092"]
    topic_catalog_map = {
        "25idc.bluesky.documents": "25idc_direct",
        "25idd.bluesky.documents": "25idd_direct",
    }
    # Create a Tiled consumer that will listen for new documents.
    consumer = DatabrokerConsumer(
        topic_catalog_map=topic_catalog_map,
        bootstrap_servers=bootstrap_servers,
        group_id="databroker_consumer",
        consumer_config={"auto.offset.reset": "latest"},
        polling_duration=1.0,
    )
    log.info("Starting Tiled consumer")
    consumer.start()


if __name__ == "__main__":
    sys.exit(main())
