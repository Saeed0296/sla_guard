FROM python:3.9-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Set environmental variables
ENV PORT=7860
ENV HOST=0.0.0.0
CMD ["python", "backend/main.py"]
