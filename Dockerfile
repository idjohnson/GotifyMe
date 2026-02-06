FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# Set default environment variables
ENV GOTIFY_ENDPOINT="https://gotify.tpk.pw"
ENV GOTIFY_USERNAME=""
ENV GOTIFY_PASSWORD=""
ENV NOTIFYPASS=""

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
