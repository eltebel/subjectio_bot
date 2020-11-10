## Table of contents
* [General info](#general-info)
* [Technologies](#technologies)
* [Setup](#setup)

## General info
It’s an open source project under the MIT license, written with Python language and Flask framework. As the database engine, MongoDB was used with Mongoengine, for bot persistent state as well as queueing tweets to be posted. The application is composed of two coupled parts:
1. Control panel, written in Flask framework, that serves the purpose of managing payloads etc. 
2. A daemon type part, that processes operations posted in the queue and makes a call to Twitter API using python library Tweepy.
The application requires Unix type operating system to run. Recommended OS is Linux Debian.
	
## Technologies
* Python
* Flask
* Tweepy
* MongoDB
	
## Setup

### install required python packages
pip -r requirements.txt

### install mongodb, uwsgi webserver
depends on your OS

### configuration
see botski/config.py file

### run control panel (simplest way)
screen -D sh backend_run.sh

### run console part
sh daemon_run.sh
