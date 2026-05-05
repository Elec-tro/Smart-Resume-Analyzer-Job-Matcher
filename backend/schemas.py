from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

class AnalysisResult(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    ats_score: int
    skills_detected: List[str]
    job_matches: List[dict]
    suggestions: List[str]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
