FROM ghcr.io/prefix-dev/pixi:0.81.0 AS beamline

# System dependencies
# git is only needed if pixi.toml defines git dependencies
RUN apt-get update
RUN apt-get install -y git qt5-default

# Build the python environment
COPY . /var/haven/
WORKDIR /var/haven/
RUN --mount=type=cache,target=/root/.cache/rattler/cache pixi install --locked --environment beamline
ENTRYPOINT ["pixi", "run", "--environment", "beamline", "--as-is"]

# # Dedicated user for running HAVEN things
RUN adduser beamlineuser
USER beamlineuser

# Configuration files. It's up to the client that runs this container
# to bind-mount the configuration folder to /etc/bluesky
ENV BLUESKY_DIR="/etc/bluesky/"
ENV HAVEN_CONFIG="/etc/bluesky/haven.toml"
ENV TILED_CONFIG="/etc/bluesky/tiled_server_config.yml"
ENV QSERVER_HTTP_SERVER_CONFIG="/etc/bluesky/qserver_http_config.yml"

###################################
# Individual beamline environments
###################################
from beamline as 9bm
ENV QSERVER_ZMQ_CONTROL_ADDRESS="tcp://abasin.xray.aps.anl.gov:60615"
ENV QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER="tcp://*:60615"
ENV QSERVER_ZMQ_INFO_ADDRESS="tcp://abasin.xray.aps.anl.gov:60625"
ENV QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER="tcp://*:60625"

from beamline as 20bm
ENV QSERVER_ZMQ_CONTROL_ADDRESS="tcp://blackcomb.xray.aps.anl.gov:60615"
ENV QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER="tcp://*:60615"
ENV QSERVER_ZMQ_INFO_ADDRESS="tcp://blackcomb.xray.aps.anl.gov:60625"
ENV QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER="tcp://*:60625"

FROM beamline as 25idc
ENV QSERVER_ZMQ_CONTROL_ADDRESS="tcp://jackson-hole.xray.aps.anl.gov:60615"
ENV QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER="tcp://*:60615"
ENV QSERVER_ZMQ_INFO_ADDRESS="tcp://jackson-hole.xray.aps.anl.gov:60625"
ENV QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER="tcp://*:60625"

FROM beamline as 25idd
ENV QSERVER_ZMQ_CONTROL_ADDRESS="tcp://jackson-hole.xray.aps.anl.gov:60616"
ENV QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER="tcp://*:60616"
ENV QSERVER_ZMQ_INFO_ADDRESS="tcp://jackson-hole.xray.aps.anl.gov:60626"
ENV QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER="tcp://*:60626"
