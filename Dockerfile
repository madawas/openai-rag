FROM python:3.11.4-slim

WORKDIR /home

# setting volume now to dev
#COPY ./oairag /home/oairag
#COPY .env /home/
COPY requirements.txt /home/

RUN pip install -r /home/requirements.txt
RUN mkdir uploads

EXPOSE 8000

CMD ["uvicorn", "oairag.main:app", "--host", "0.0.0.0", "--reload"]