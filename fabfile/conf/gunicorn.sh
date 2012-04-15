#!/bin/bash
set -e

LOGDIR="{{ env.log_path }}/gunicorn"
LOGFILE="$LOGDIR/gunicorn.log"
PIDFILE="$LOGDIR/gunicorn.pid"

VIRTUALDIR="{{env.path}}"

ADDRESS='127.0.0.1:{{ env.gunicorn_port }}'
NUM_WORKERS={{ env.gunicorn_worker_count }}
# user/group to run as
USER={{ gunicorn_user }}
GROUP={{ gunicorn_group }}

#DJANGO_SETTINGS_MODULE='production.settings'
cd $VIRTUALDIR/current/project

#use virtualenv
source $VIRTUALDIR/bin/activate

test -d $LOGDIR || mkdir -p $LOGDIR
exec gunicorn_django -w $NUM_WORKERS --user=$USER --group=$GROUP --log-level=debug --log-file=$LOGFILE --pid=$PIDFILE --bind=$ADDRESS 2>>$LOGFILE
