## 백엔드 실행 방법

1. env 파일 설정
   - OPENAI_API_KEY, POSTGRES_USER, POSTGRES_PASSWORD 설정
   - DB_HOST=localhost
   - DB_PORT=5433
   - POSTGRES_DB=jumokase_db
2. docker-compose up -d
3. python load_data.py
4. python load_recommendations.py
5. uvicorn main:app --port 8005 --reload
