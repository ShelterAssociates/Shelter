#Script to renew the certificate file.
#
#docker stop kobodocker_nginx_1

sudo service nginx stop
cd /opt/letsencrypt/

#sudo -H ./letsencrypt-auto certonly --standalone --renew-by-default -d dk.shelter-associates.org -d kc.shelter-associates.org -d enketo.shelter-associates.org -d app.shelter-associates.org -d graphs.shelter-associates.org
sudo -H ./letsencrypt-auto certonly --standalone --renew-by-default -d app.shelter-associates.org

#sudo cp /etc/letsencrypt/live/app.shelter-associates.org/fullchain.pem ssl.crt

#sudo cp /etc/letsencrypt/live/app.shelter-associates.org/privkey.pem ssl.key

sudo service nginx restart
#docker start kobodocker_nginx_1

