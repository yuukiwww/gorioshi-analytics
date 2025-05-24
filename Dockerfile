FROM python:3.13.3
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED 1
CMD ["fastapi", "run", "--workers", "5"]
