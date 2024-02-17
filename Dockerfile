FROM python:3.12.2-slim

WORKDIR /home

COPY ./oairag /home/oairag
COPY requirements.txt /home/

RUN pip install -r /home/requirements.txt
RUN mkdir uploads

RUN addgroup --gid 10016 fastapi && \
    adduser --system --no-create-home --uid 10020 --ingroup fastapi raguser
USER 10020

EXPOSE 8000

CMD ["uvicorn", "oairag.main:app", "--host", "0.0.0.0", "--reload"]