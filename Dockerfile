FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY poop_bot.py .
CMD ["python", "poop_bot.py"]