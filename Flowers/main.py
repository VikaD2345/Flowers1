from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Bouquet 
from database import get_db 

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Flowers API работает!"}


@app.get("/popular")
def get_popular(db: Session = Depends(get_db)):
    popular_bouquets = db.query(Bouquet).filter(Bouquet.is_popular == True).all()
    return popular_bouquets

@app.get("/bouquets")
def get_all_bouquets(db: Session = Depends(get_db)):
    all_bouquets = db.query(Bouquet).all()
    return all_bouquets

