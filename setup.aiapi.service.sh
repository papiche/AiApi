#!/bin/bash
set -euo pipefail
[ $(id -u) -eq 0 ] && echo "LANCEMENT root INTERDIT (use sudo user). " && exit 1
cat aiapi.service.tpl | sed "s~_USER_~$USER~g" | sed "s~_MY_PATH_~$(pwd)~" > /tmp/aiapi.service

cat /tmp/aiapi.service
sudo cp /tmp/aiapi.service /etc/systemd/system/aiapi.service

sudo systemctl daemon-reload
sudo systemctl enable aiapi
sudo systemctl restart aiapi
