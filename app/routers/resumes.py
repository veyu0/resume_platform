from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models
from app.database import get_db
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.utils import SECRET_KEY, ALGORITHM
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

router = APIRouter()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/", response_model=schemas.Resume)
def create_resume(resume: schemas.ResumeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_resume = models.Resume(**resume.dict(), owner_id=current_user.id)
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    logger.info(f"Resume created with title: {resume.title} for user: {current_user.email}")
    return new_resume

@router.get("/", response_model=List[schemas.Resume])
def get_resumes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    resumes = db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).all()
    return resumes

@router.get("/{resume_id}", response_model=schemas.Resume)
def get_resume(resume_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.put("/{resume_id}", response_model=schemas.Resume)
def update_resume(resume_id: int, resume: schemas.ResumeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    db_resume.title = resume.title
    db_resume.content = resume.content
    db.commit()
    db.refresh(db_resume)
    logger.info(f"Resume {resume_id} successfully changed")
    return db_resume

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(db_resume)
    db.commit()
    logger.info(f"Resume {resume_id} successfully deleted")
    return

@router.post("/{resume_id}/improve")
def improve_resume(resume_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    improved_content = db_resume.content + "\n[Improved]"
    logger.info(f"Resume {resume_id} successfully improved")
    return {"improved_content": improved_content}