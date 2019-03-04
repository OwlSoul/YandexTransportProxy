# Dockerfile for Yandex Transport Monitor
# Architectures: armhf (Orange PI, Raspberry PI)
#                x86-64

# Use Ubuntu 18.04 as basis
FROM ubuntu:18.04

# ----- CHANGE THESE ARGUMENTS TO YOUR DESIRES ----- #
# -- ИЗМЕНИТЕ ДАННЫЕ АРГУМЕНТЫ ДЛЯ ВАШЕЙ СИТУАЦИИ -- #
# TimeZone / Часовой Пояс
ARG timezone=Europe/Moscow

# -------------------------------------------------- #

RUN apt-get update -y

# Dealing with goddamn locales
RUN apt-get install -y locales=2.27-3ubuntu1
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

# Setting the goddamn TimeZone
RUN apt-get install -y tzdata=2018i-0ubuntu0.18.04
ENV TZ=${timezone}
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone 

# Install wget
RUN apt-get install -y wget=1.19.4-1ubuntu2.1

# Install unzip
RUN apt-get install -y unzip=6.0-21ubuntu1

# Install Chromium browser
RUN apt-get install -y chromium-browser=71.0.3578.98-0ubuntu0.18.04.1

# Installing WebDriver, note that it has the same version as Chromium
RUN apt-get install -y chromium-chromedriver=71.0.3578.98-0ubuntu0.18.04.1

# Because life can't be easy, isn't it?
# psycopg2-binary refuses to install on armhf without this thing.
RUN apt-get install -y libpq-dev=10.6-0ubuntu0.18.04.1

# It seems life is suffering and you should suffer till you the very end.
# lxml requires, surprise, xml libraries.
# This is not a problem on x86-64 Ubuntu, but it is on armhf machines.
RUN apt-get install -y libxml2-dev=2.9.4+dfsg1-6.1ubuntu1.2
RUN apt-get install -y libxslt1-dev=1.1.29-5

# Install python3
RUN apt-get install -y python3=3.6.7-1~18.04

# Install python3-pip
RUN apt-get install -y python3-pip=9.0.1-2.3~ubuntu1

# Install required python packages
RUN pip3 install psycopg2-binary==2.7.6.1
RUN pip3 install selenium==3.141.0
RUN pip3 install setproctitle==1.1.10
RUN pip3 install beautifulsoup4==4.6.0
RUN pip3 install lxml==4.2.1

# Creating the user
RUN mkdir -p /home/ytmonitor
RUN useradd ytmonitor --home /home/ytmonitor --shell /bin/bash
RUN mkdir -p /home/ytmonitor

# Copying the project
ADD ytm_wd /home/ytmonitor
ADD ytm_pageparser.py /home/ytmonitor

# Setting permissions
RUN chown -R ytmonitor:ytmonitor /home/ytmonitor
WORKDIR /home/ytmonitor
