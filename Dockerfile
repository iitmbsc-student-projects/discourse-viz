FROM continuumio/miniconda3

WORKDIR /app

COPY . /app

# RUN pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple && pip cache purge && conda clean --all

RUN pip install -r requirements.txt && pip cache purge && conda clean --all

EXPOSE 5000

ENV FLASK_APP=app.py

CMD ["python", "app.py"]