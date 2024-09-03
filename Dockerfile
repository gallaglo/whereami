FROM python:3.12.1-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
  wget && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  wget -O /bin/curl https://github.com/moparisthebest/static-curl/releases/download/v8.2.1/curl-amd64 && \ 
  chmod +x /bin/curl

WORKDIR /app
COPY . ./
RUN pip install -r requirements.txt

EXPOSE 8080
ENTRYPOINT ["python3", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
