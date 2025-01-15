# 1. API Architecture
clean architecture
- api
- service
- repository


# 2. Models
suport request/response
- models: entier object
- scheme: request/response model (dto)

# 3. How to run?
0. from root folder, go to the api network folder: "cd sdk/network"
1. run in terminal "uvicorn app.main:app --reload"
2. options
    1. host: "--host 0.0.0.0"
    2. port: "--port 8000"

3. view open api: http://localhost:8000/docs


# 4. How to test?
1. run "pytest"
2. coverage with stdout: "pytest --cov=app --cov-report=term-missing"
3. coverage with html "pytest --cov=app --cov-report=html" 