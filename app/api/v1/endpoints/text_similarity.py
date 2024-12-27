from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sklearn.metrics.pairwise import cosine_similarity
import json
import cohere

from app.schemas.text_similarity import Job
from app.core.config import settings
from app.api.api_resonse import error_response, success_response

similarity_router = APIRouter()
co=cohere.ClientV2(settings.COHERE_API_KEY)


def calculate_similarity(text1, text2):
    docs=[text1,text2]

    embeddings1 = co.embed(texts=docs, 
                         model='embed-english-v3.0', 
                         input_type="search_document",
                         embedding_types=["float"]).embeddings.float
    
    embedding1 = [embeddings1[0]]
    embedding2 = [embeddings1[1]]
    
    similarity = cosine_similarity(embedding1, embedding2)[0][0]

    return similarity




@similarity_router.post("/similarity")
async def text_similarity(role: str = Form(...), description: str = Form(...), dificulty_level: str = Form(...), file: UploadFile = File(...)):
    job = Job(role=role, description=description, difficulty_level=dificulty_level)
    try:
        job_description=job.description
        if file.filename.endswith(".json"):
            contents = await file.read()
            data = json.loads(contents.decode("utf-8"))['data']
        else:
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload a JSON file.")
        
        simialarity_score=calculate_similarity(job_description,data)

        
        return success_response(data=simialarity_score)
    except Exception as e:
        raise error_response(message=str(e))
