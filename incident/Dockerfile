FROM python:3.12.11-slim-bookworm
WORKDIR /opt/receiver
RUN groupadd --system --gid 10002 receiver && useradd --system --uid 10002 --gid receiver receiver
COPY --chown=receiver:receiver incident/receiver.py .
RUN mkdir /artifacts && chown receiver:receiver /artifacts
USER 10002:10002
EXPOSE 8081
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/healthz')"]
CMD ["python", "receiver.py"]
