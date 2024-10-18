# Base Image with CUDA 11.8
#FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu20.04
# FROM nvidia/cuda:12.6.0-cudnn-devel-ubuntu20.04

# Latch environment building
COPY --from=812206152185.dkr.ecr.us-west-2.amazonaws.com/latch-base-cuda:fe0b-main /bin/flytectl /bin/flytectl
WORKDIR /root

ENV VENV /opt/venv
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONPATH /root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y libsm6 libxext6 libxrender-dev build-essential procps rsync openssh-server

RUN apt-get install -y software-properties-common &&\
    add-apt-repository -y ppa:deadsnakes/ppa &&\
    apt-get install -y python3.9 python3-pip python3.9-distutils curl

RUN python3.9 -m pip install --upgrade pip && python3.9 -m pip install awscli

RUN curl -L https://github.com/peak/s5cmd/releases/download/v2.0.0/s5cmd_2.0.0_Linux-64bit.tar.gz -o s5cmd_2.0.0_Linux-64bit.tar.gz &&\
    tar -xzvf s5cmd_2.0.0_Linux-64bit.tar.gz &&\
    mv s5cmd /bin/ &&\
    rm CHANGELOG.md LICENSE README.md

COPY --from=812206152185.dkr.ecr.us-west-2.amazonaws.com/latch-base-cuda:fe0b-main /root/Makefile /root/Makefile
COPY --from=812206152185.dkr.ecr.us-west-2.amazonaws.com/latch-base-cuda:fe0b-main /root/flytekit.config /root/flytekit.config

WORKDIR /tmp/docker-build/work/

SHELL [ \
    "/usr/bin/env", "bash", \
    "-o", "errexit", \
    "-o", "pipefail", \
    "-o", "nounset", \
    "-o", "verbose", \
    "-o", "errtrace", \
    "-O", "inherit_errexit", \
    "-O", "shift_verbose", \
    "-c" \
]
ENV TZ='Etc/UTC'
ENV LANG='en_US.UTF-8'

ARG DEBIAN_FRONTEND=noninteractive

# Install system requirements
RUN apt-get update --yes && \
    xargs apt-get install --yes aria2 git wget unzip curl fuse && \
    apt-get install --fix-broken

# ObjectiveFS
RUN curl --location --fail --remote-name https://objectivefs.com/user/download/an7dzrz65/objectivefs_7.2_amd64.deb && \
    dpkg -i objectivefs_7.2_amd64.deb && \
    mkdir /etc/objectivefs.env

COPY credentials/* /etc/objectivefs.env/

RUN apt-get install --yes pkg-config libfuse-dev

# ObjectiveFS performance tuning
ENV CACHESIZE="50Gi"
ENV DISKCACHE_SIZE="200Gi"

# Latch SDK
# DO NOT REMOVE
RUN pip install latch==2.53.0
RUN mkdir /opt/latch

# Install Mambaforge
RUN apt-get update --yes && \
    apt-get install --yes curl && \
    curl \
        --location \
        --fail \
        --remote-name \
        https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh && \
    `# Docs for -b and -p flags: https://docs.anaconda.com/anaconda/install/silent-mode/#linux-macos` \
    bash Mambaforge-Linux-x86_64.sh -b -p /opt/conda -u && \
    rm Mambaforge-Linux-x86_64.sh

# Set conda PATH
ENV PATH=/opt/conda/bin:$PATH

# Build conda environment
COPY environment.yaml /opt/latch/environment.yaml
RUN mamba env create \
    --file /opt/latch/environment.yaml \
    --name RF2NA
ENV PATH=/opt/conda/envs/RF2NA/bin:$PATH

RUN conda run -n RF2NA pip install dgl==2.1.0 -f https://data.dgl.ai/wheels/cu121/repo.html && \
    conda run -n RF2NA pip install git+https://github.com/NVIDIA/dllogger#egg=dllogger

RUN git clone https://github.com/uw-ipd/RoseTTAFold2NA.git  && \
    cd RoseTTAFold2NA  && \
    conda run -n RF2NA pip install -r /tmp/docker-build/work/RoseTTAFold2NA/SE3Transformer/requirements.txt && \
    conda run -n RF2NA pip install /tmp/docker-build/work/RoseTTAFold2NA/SE3Transformer/

ENV DGLBACKEND=pytorch

# Copy workflow data (use .dockerignore to skip files)
COPY . /root/

# Latch workflow registration metadata
# DO NOT CHANGE
ARG tag
# DO NOT CHANGE
ENV FLYTE_INTERNAL_IMAGE $tag

WORKDIR /root
