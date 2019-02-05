#!/bin/bash
set -e
LOGFILE=/var/log/gunicorn/shelter.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=4
# user/group to run as
USER=ubuntu
GROUP=ubuntu
cd /srv/Shelter/
source /srv/Shelter/ENV/bin/activate
#pip freeze
test -d $LOGDIR || mkdir -p $LOGDIR
exec /srv/Shelter/ENV/bin/gunicorn -b 0.0.0.0:8011 -w $NUM_WORKERS --timeout 600 --user=$USER --group=$GROUP --log-level=info --log-file=$LOGFILE 2>>$LOGFILE shelter.wsgi:application
