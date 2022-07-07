FROM hysds/pge-base

MAINTAINER gmanipon "gmanipon@jpl.nasa.gov"
LABEL description="MSAS PGE container"

ARG id
ARG gid

# create work directory
RUN set -ex \
 && mkdir -p /data/work \
 && chmod -R 755 /data \
 && chown -R ops:ops /data

# copy job repo and install gdal
COPY . /home/ops/verdi/ops/measures
RUN set -ex \
 && sudo chown -R ops:ops /home/ops/verdi/ops/measures \
 && sudo yum update -y \
 && sudo yum install -y gdal gdal-devel gdal-libs gdal-python \
 && sudo yum install -y /home/ops/verdi/ops/measures/docker/reqs/gdal-hysds-2.1-1.x86_64.rpm \
 && sudo yum clean all \
 && sudo rm -rf /home/ops/verdi/ops/measures/docker/reqs /var/cache/yum

# set user
USER ops

# copy packages
RUN set -ex \
 && source /home/ops/verdi/bin/activate \
 && mv /home/ops/verdi/ops/measures/pydap /home/ops/verdi/ops/pydap \
 && cd /home/ops/verdi/ops/pydap \
 && pip install -e . \
 && cd /home/ops/verdi/ops/measures \
 && pip install -e .

# set entrypoint
WORKDIR /home/ops
CMD ["/bin/bash", "--login"]
