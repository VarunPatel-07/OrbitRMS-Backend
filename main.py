from fastapi import FastAPI, Request
from routes.auth.login import login

app = FastAPI()
app.include_router(login)