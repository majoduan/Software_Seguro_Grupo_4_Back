from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def add_middlewares(app: FastAPI) -> None:
    origins = [
        # "http://localhost:5173",
        # "http://localhost:3000" # URLs del frontend
        #"*"
        "https://software-seguro-grupo-4-front.vercel.app"
    ]
#TODO: Cambiar los headers y metodos permitidos
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
