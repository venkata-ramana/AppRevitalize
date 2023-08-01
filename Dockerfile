FROM python:latest

WORKDIR /app

COPY run.sh .
COPY multi-repo-log4j-updater.py .

CMD ["sh", "run.sh"]