---
description: Deploy PoopTrackerBot to AWS EC2 Free Tier (Singapore), same instance as StickerCapsBot
---

## EC2 Instance
- IP: `13.212.210.231`
- PEM: `C:\CODING_2026\StickerCapsBot\stickercapsbot-key.pem`
- SSH: `ssh -i stickercapsbot-key.pem ubuntu@13.212.210.231`

## 1. Клонировать репозиторий на сервере
```bash
git clone https://github.com/SandresAFK/PoopTrackerBot.git
cd PoopTrackerBot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Создать .env файл
```bash
nano /home/ubuntu/PoopTrackerBot/.env
```
Вставить:
```
BOT_TOKEN=your_token_here
DB_PATH=/home/ubuntu/PoopTrackerBot/poop.db
```
Сохранить: Ctrl+O → Enter → Ctrl+X

## 3. Скопировать базу данных (с локальной машины)
```powershell
scp -i C:\CODING_2026\StickerCapsBot\stickercapsbot-key.pem C:\CODING_2026\PoopTrackerBot\poop.db ubuntu@13.212.210.231:/home/ubuntu/PoopTrackerBot/poop.db
```

## 4. Создать systemd сервис
```bash
sudo nano /etc/systemd/system/pooptrackerbot.service
```
Вставить:
```ini
[Unit]
Description=PoopTrackerBot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/PoopTrackerBot
ExecStart=/home/ubuntu/PoopTrackerBot/.venv/bin/python poop_bot.py
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/PoopTrackerBot/.env

[Install]
WantedBy=multi-user.target
```
Сохранить: Ctrl+O → Enter → Ctrl+X

## 5. Запустить бот
```bash
sudo systemctl daemon-reload
sudo systemctl enable pooptrackerbot
sudo systemctl start pooptrackerbot
sudo systemctl status pooptrackerbot
```

## 6. Проверить логи
```bash
journalctl -u pooptrackerbot -f
```

## Обновление бота (после git push)
```bash
cd /home/ubuntu/PoopTrackerBot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pooptrackerbot
```
