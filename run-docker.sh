docker build -t crowd . && docker run --env-file .env -p 8000:8000 crowd
