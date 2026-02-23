FROM python:3.11-slim

WORKDIR /app

# Install flask-apcore from local source with mcp extra
COPY . /src/flask-apcore
RUN pip install /src/flask-apcore[mcp]

COPY examples/demo/ /app/

ENV FLASK_APP=app.py
EXPOSE 9100

CMD ["bash", "entrypoint.sh"]
