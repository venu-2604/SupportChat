from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    otp: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FAQ(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str


class Ticket(BaseModel):
    id: Optional[int] = None
    user_email: EmailStr
    customer_name: Optional[str] = None
    subject: str
    category: Optional[str] = None
    description: str
    status: Optional[str] = "open"  # open, in_progress, escalated, resolved, closed
    priority: Optional[str] = "medium"  # low, medium, high, urgent
    session_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TicketUpdate(BaseModel):
    # All fields optional for PATCH semantics
    user_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    session_id: Optional[str] = None


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str


