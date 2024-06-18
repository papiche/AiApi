[Unit]
Description=AiApi Service
After=network.target

[Service]
User=_USER_
Group=_USER_
WorkingDirectory=_MY_PATH_
ExecStart=/usr/bin/python3 _MY_PATH_/api.py --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
