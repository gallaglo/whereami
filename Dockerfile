FROM python:3.12.1-slim

WORKDIR /app
COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8080
ENTRYPOINT ["python3", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
