import os
import shutil
import json
from typing import List
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models, schemas, auth, analyzer

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HireSense AI Resume Analyzer")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

resume_analyzer = analyzer.ResumeAnalyzer()

@app.post("/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = auth.create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer", "user_id": db_user.id}

@app.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Save file temporarily
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Extract text
    text = ""
    if file.filename.endswith(".pdf"):
        text = resume_analyzer.extract_text_from_pdf(file_path)
    elif file.filename.endswith(".docx"):
        text = resume_analyzer.extract_text_from_docx(file_path)
    else:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    # Analyze
    found_skills = resume_analyzer.get_extracted_skills(text)
    ats_score = resume_analyzer.calculate_ats_score(text, found_skills)
    job_matches = resume_analyzer.match_job_roles(found_skills)
    suggestions = resume_analyzer.get_suggestions(text, found_skills)
    
    # Store in DB
    new_resume = models.Resume(filename=file.filename, user_id=current_user.id)
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    analysis_record = models.Analysis(
        resume_id=new_resume.id,
        ats_score=ats_score,
        skills_detected=json.dumps(found_skills),
        job_matches=json.dumps(job_matches),
        suggestions=json.dumps(suggestions)
    )
    db.add(analysis_record)
    db.commit()
    
    # Clean up
    os.remove(file_path)
    
    return {
        "id": new_resume.id,
        "filename": file.filename,
        "ats_score": ats_score,
        "skills_detected": found_skills,
        "job_matches": job_matches,
        "suggestions": suggestions
    }

@app.get("/history", response_model=List[schemas.AnalysisResult])
def get_history(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    resumes = db.query(models.Resume).filter(models.Resume.user_id == current_user.id).all()
    results = []
    for r in resumes:
        if r.analysis:
            results.append({
                "id": r.id,
                "filename": r.filename,
                "upload_date": r.upload_date,
                "ats_score": r.analysis.ats_score,
                "skills_detected": json.loads(r.analysis.skills_detected),
                "job_matches": json.loads(r.analysis.job_matches),
                "suggestions": json.loads(r.analysis.suggestions)
            })
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
