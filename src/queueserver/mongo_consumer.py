import os
import sys
from functools import partial

# This environmental variable needs to be set before importing haven
os.environ["HAVEN_CONFIG_FILES"] = f"{os.environ['BLUESKY_DIR']}/iconfig.toml"

import msgpack
import msgpack_numpy as mpn
from bluesky_kafka import MongoConsumer

import haven


def main():
    """Launch the mongo consumer."""
    bootstrap_servers = "localhost:9092"

    # Determine the mongo DB URI from the databroker/intake configuration
    catalog_name = haven.load_config()["database"]["databroker"]["catalog"]
    catalog = haven.load_catalog(name=catalog_name)
    host, port = catalog._resource_collection.database.client.address
    mongo_uri = f"mongodb://{host}:{port}"

    if mongo_uri is None:
        raise AttributeError("Environment variable BLUESKY_MONGO_URI " "must be set.")

    kafka_deserializer = partial(msgpack.loads, object_hook=mpn.decode)
    auto_offset_reset = "latest"
    topics = ["s25idc_queueserver", "s25idd_queueserver"]

    topic_database_map = {
        "s25idc_queueserver": "25idc-bluesky",
        "s25idd_queueserver": "25idd-bluesky",
    }

    # Create a MongoConsumer that will automatically listen to new beamline topics.
    # The parameter metadata.max.age.ms determines how often the consumer will check for
    # new topics. The default value is 5000ms.
    mongo_consumer = MongoConsumer(
        mongo_uri,
        topic_database_map,
        tls=False,
        topics=topics,
        bootstrap_servers=bootstrap_servers,
        group_id="mongodb",
        consumer_config={"auto.offset.reset": auto_offset_reset},
        polling_duration=1.0,
        deserializer=kafka_deserializer,
    )

    mongo_consumer.start()


if __name__ == "__main__":
    sys.exit(main())
