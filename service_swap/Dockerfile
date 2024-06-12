FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y libgl1
RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


# Run Django development server
CMD ["python", "consumption_swap.py"]
