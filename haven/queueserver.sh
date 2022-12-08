# BLUESKY_DIR="${HOME}/bluesky_25idc"

# #!/bin/bash

# # manage the bluesky queueserver

# #--------------------
# # change the program defaults here
# CONDA_ENVIRONMENT=haven
# # DATABROKER_CATALOG=training
# #--------------------

# # activate conda environment

# # In GitHub Actions workflow,
# # $CONDA is an environment variable pointing to the
# # root of the miniconda directory
# if [ "${CONDA}" == "" ] ; then
#     CONDA=/APSshare/miniconda/x86_64
#     if [ ! -d "${CONDA}" ]; then
# 	if [ "${CONDA_EXE}" != "" ]; then
# 	    # CONDA_EXE is the conda exectuable
# 	    CONDA=$(dirname $(dirname $(readlink -f "${CONDA_EXE}")))
# 	else
# 	    # fallback
# 	    CONDA=/opt/miniconda3
# 	fi
#     fi
# fi
# CONDA_BASE_DIR="${CONDA}/bin"

# # In GitHub Actions workflow,
# # $ENV_NAME is an environment variable naming the conda environment to be used
# if [ -z "${ENV_NAME}" ] ; then
#     ENV_NAME="${CONDA_ENVIRONMENT}"
# fi

# # echo "Environment: $(env | sort)"

# source "${CONDA_BASE_DIR}/activate" "${ENV_NAME}"

# SHELL_SCRIPT_NAME=${BASH_SOURCE:-${0}}
# # if [ -z "$STARTUP_DIR" ] ; then
# #     # If no startup dir is specified, use the directory with this script
# #     STARTUP_DIR=$(dirname "${SHELL_SCRIPT_NAME}")
# #     fi

# source "${HOME}/micromamba/etc/profile.d/micromamba.sh"
# eval "$(micromamba shell hook --shell=bash)"
# # mamba init
# micromamba activate ${CONDA_ENVIRONMENT}
# micromamba list
export HAVEN_CONFIG_FILES="${BLUESKY_DIR}/iconfig.toml"
start-re-manager \
    --startup-script ${HOME}/src/haven/haven/queueserver_startup.py \
    --existing-plans-devices ${BLUESKY_DIR}/queueserver_existing_plans_and_devices.yaml \
    --user-group-permissions ${BLUESKY_DIR}/queueserver_user_group_permissions.yaml \
    --databroker-config s25idc \
    --kafka-topic 25idc_queueserver \
    --keep-re \
    --update-existing-plans-devices ENVIRONMENT_OPEN

