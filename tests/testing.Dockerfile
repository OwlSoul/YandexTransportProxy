# Dockerfile for Yandex Transport Monitor Tests
# Architectures: armhf (Orange PI, Raspberry PI)
#                x86-64

# Use Ubuntu 18.04 as basis
FROM ubuntu:18.04

# ----- CHANGE THESE ARGUMENTS TO YOUR DESIRES ----- #
# -- ИЗМЕНИТЕ ДАННЫЕ АРГУМЕНТЫ ДЛЯ ВАШЕЙ СИТУАЦИИ -- #
# TimeZone / Часовой Пояс
ARG timezone=Europe/Moscow

# -------------------------------------------------- #

# Setting frontend to non-interactive, no questions asked, ESPECIALLY for locales.
ENV DEBIAN_FRONTEND=noninteractive

# Install all required software, right way.
# We're using all latest package versions here. Risky.
RUN apt-get update && \
    apt-get install -y \
    locales \
    tzdata \
    # Chromium and chromedriver, latest versions.
    chromium-browser \
    chromium-chromedriver \
    # Because life can't be easy, isn't it?
    # psycopg2-binary refuses to install on armhf without this thing.
    libpq-dev \
    # It seems life is suffering and you should suffer till you the very end.
    # lxml requires, surprise, xml libraries.
    # This is not a problem on x86-64 Ubuntu, but it is on armhf machines.
    libxml2-dev \
    libxslt1-dev \
    # Install python3
    python3 \
    # Install python3-pip
    python3-pip

# Install required python packages
RUN pip3 install psycopg2-binary \
                 selenium \
                 setproctitle \
                 beautifulsoup4 \
                 lxml

# Install pytest, separately, so previous step will be cached
RUN pip3 install pytest \
                 pytest-progress \
                 pytest-rerunfailures \
                 pytest-timeout

# Dealing with goddamn locales
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

# Setting the goddamn TimeZone
ENV TZ=${timezone}
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone 

# Cleaning
RUN apt-get clean

# Creating the user
RUN mkdir -p /home/transport_proxy
RUN useradd transport_proxy --home /home/transport_proxy --shell /bin/bash

# Copying the project
ADD yandex_transport_core/ /home/transport_proxy/yandex_transport_core
ADD transport_proxy.py /home/transport_proxy

# Copying tests
ADD tests/test* /home/transport_proxy/tests/
ADD execute_tests.sh /home/transport_proxy

# Setting permissions
RUN chown -R transport_proxy:transport_proxy /home/transport_proxy
WORKDIR /home/transport_proxy

# Setting up entry point for this container, it's designed to run as an executable.
# ENTRYPOINT HERE
USER transport_proxy:transport_proxy
CMD /home/transport_proxy/execute_tests.sh
