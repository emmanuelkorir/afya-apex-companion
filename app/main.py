from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database.db import connect_db, disconnect_db

# Import your CRUD functions
from app.database import crud 

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    print("Connected to Supabase via Prisma!")
    yield
    await disconnect_db()
    print("Disconnected from Supabase.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "EMR Companion API is running with Prisma!"}

# --- NEW TEST ENDPOINT ---
@app.get("/test-db")
async def test_database():
    test_user_id = "doctor_telegram_123"
    
    # 1. Create a fake Playwright session state (JSON)
    dummy_cookie_state = {
        "cookies": [
            {"name": "ASP.NET_SessionId", "value": "fake_token_abc123", "domain": "dummy-emr.local"}
        ],
        "origins": []
    }
    
    try:
        # 2. Save it to Supabase (Upsert)
        await crud.save_session(test_user_id, dummy_cookie_state)
        
        # 3. Read it back from Supabase
        retrieved_state = await crud.get_session(test_user_id)
        
        return {
            "status": "success",
            "message": "Successfully wrote and read from Supabase!",
            "data_retrieved": retrieved_state
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}