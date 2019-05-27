#Script to renew the certificate file.
#
docker stop kobodocker_nginx_1

cd /opt/letsencrypt/

sudo -H ./letsencrypt-auto certonly --standalone --renew-by-default -d dk.shelter-associates.org -d kc.shelter-associates.org -d enketo.shelter-associates.org -d app.shelter-associates.org -d graphs.shelter-associates.org

cd /srv/kobo-docker/secrets/

sudo cp /etc/letsencrypt/live/dk.shelter-associates.org/fullchain.pem ssl.crt

sudo cp /etc/letsencrypt/live/dk.shelter-associates.org/privkey.pem ssl.key

docker start kobodocker_nginx_1

