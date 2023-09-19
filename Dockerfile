FROM python:3.10.13-bullseye
RUN rm /bin/sh && ln -s /bin/bash /bin/sh

WORKDIR /vlad/track_rates

COPY requirements.txt .
RUN python -m venv venv
RUN source /vlad/track_rates/venv/bin/activate
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000