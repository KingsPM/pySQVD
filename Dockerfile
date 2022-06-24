FROM python:3.8

# simple docker container to load folders with the runLoader into SQVD
# run as follows:
#     docker run -it -e SQVDHOST=<SQVD_API_HOST> -e SQVDUSER=<SQVD_USER> -e SQVDPASS=<SQVD_PASSWORD> \
#         -v <PATH_TO_RUNFOLDER>:/data --rm seglh/pysqvd:molpath /data
#
# E.g.
#     docker run -it -e SQVDHOST=172.17.0.1:3000 -e SQVDUSER=admin -e SQVDPASS=Kings123 \
#         -v /srv/work/analysis/RCP999:/data --rm seglh/pysqvd:molpath /data

RUN apt-get update && apt-get install -y git tabix
WORKDIR /pysqvd
ADD . /pysqvd
RUN python setup.py install
ENTRYPOINT ["python", "scripts/runLoader.py"]



