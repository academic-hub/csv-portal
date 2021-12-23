FROM python:3.8.10-slim-buster as base
FROM base as builder
RUN mkdir /install
WORKDIR /install
COPY ./requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN pip install --prefix=/install -r /requirements.txt --no-cache-dir 
# RUN pip install --install-option="--prefix=/install" -r /requirements.txt --no-cache-dir
FROM base
COPY --from=builder /install /usr/local
COPY . /app
# RUN pip install marshmallow
WORKDIR /app

EXPOSE 8051
CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.baseUrlPath", "dataportal"]

