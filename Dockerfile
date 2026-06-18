FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Индекс базы знаний лучше собрать заранее и примонтировать папку data/.
# Если что — собрать можно так: python -m scripts.build_index
CMD ["python", "-m", "app.bot"]
