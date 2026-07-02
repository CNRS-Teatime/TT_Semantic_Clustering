FROM python:3.12-bookworm

LABEL authors="Marwan Ait Addi-Russier"
LABEL source.repo="https://github.com/CNRS-Teatime/TEATIME_PhD_Experiments"

ADD requirements.txt .
ADD . .

RUN pip install -r requirements.txt

CMD ["python", "clustering.py"]