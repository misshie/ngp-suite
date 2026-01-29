import base64
import csv
import pickle
import secrets
import time
import json
import cv2
from typing import Annotated, List, Optional
from lib.encode import *
from lib.evaluation import *
from pydantic import BaseModel
from lib.face_alignment import *
from contextlib import asynccontextmanager
from lib.utils_functions import readb64, encodeb64
from datetime import datetime
from lib.pubcasefinder import query_pubcasefinder
from lib.integrator import integrate_json

from fastapi import Depends, FastAPI, HTTPException, status, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import os

security = HTTPBasic()

# Loaded at startup: syndrome name -> {"(Intercept)": str, "syn_scores": str}
_synds_probabilities_dict = {}

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

USERNAME = config.get('username')
PASSWORD = config.get('password')

def get_current_username(
        credentials: Annotated[HTTPBasicCredentials, Depends(security)]
    ):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = USERNAME.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = PASSWORD.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def _load_synds_probabilities_dict():
    path = os.path.join("data", "transformation_probabilities_07052025.csv")
    if not os.path.isfile(path):
        return {}
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name") or row.get("disorder_id")
            if name is None and row:
                name = list(row.keys())[0]
                name = row.get(name)
            if not name:
                continue
            out[name] = {k: v for k, v in row.items() if k != "name" and k != "disorder_id" and v != ""}
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _models
    global _device
    global _cropper_model
    global _gallery_df
    global _images_synds_dict
    global _images_genes_dict
    global _genes_metadata_dict
    global _synds_metadata_dict
    global _synds_probabilities_dict
    _models = get_models()
    _cropper_model, _device = load_cropper_model()
    _synds_probabilities_dict = _load_synds_probabilities_dict()
    # Load synd dict (v1.1.2 metadata)
    with open(os.path.join("data", "image_gene_and_syndrome_metadata_pp4_19112025_v112.p"), "rb") as f:
        data = pickle.load(f)
    _images_synds_dict = data["disorder_level_metadata"]
    _images_genes_dict = data["gene_level_metadata"]
    _genes_metadata_dict = data["gene_metadata"]
    _synds_metadata_dict = data["disorder_metadata"]
    _gallery_df = get_gallery_encodings_set(_images_synds_dict)
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000", # Vue.js: npm run dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# --- Pydantic Models for API Requests ---
class ImageRequest(BaseModel):
    img: str

class PredictRequest(BaseModel):
    img: str
    hpo_ids: Optional[List[str]] = None


@api_router.post("/predict")
async def predict_endpoint(username: Annotated[str, Depends(get_current_username)], request_data: PredictRequest):
    img = readb64(request_data.img)
    hpo_ids = request_data.hpo_ids

    if hpo_ids:
        print(f"Received HPO IDs: {hpo_ids}")
    else:
        print("No HPO IDs were provided.")

    start_time = time.time()
    
    try:
        aligned_img = face_align_crop(_cropper_model, img, _device)
    except Exception as e:
        return {"message": "Face alignment error."}
    align_time = time.time()
    try:
        encoding = encode(_models, 'cpu', aligned_img, False, False)
    except Exception as e:
        return {"message": "Encoding error."}
    encode_time = time.time()
 
    try:
        # Step 1: Run the original GestaltMatcher analysis
        gestaltmatcher_result = predict(encoding,
                                      _gallery_df,
                                      _images_synds_dict,
                                      _images_genes_dict,
                                      _genes_metadata_dict,
                                      _synds_metadata_dict,
                                      _synds_probabilities_dict)

        # Step 2: If HPO IDs are provided, query PubCaseFinder
        if hpo_ids:
            pubcasefinder_result = query_pubcasefinder(hpo_ids)
            final_result = gestaltmatcher_result.copy()
            final_result['pubcasefinder'] = pubcasefinder_result
            final_result['queried_hpo_ids'] = hpo_ids
        else:
            final_result = gestaltmatcher_result

    except Exception as e:
        print(f"Evaluation or combination error: {e}")
        return {"message": "Evaluation error."}
    finished_time = time.time()

    print('Crop: {:.2f}s'.format(align_time-start_time))
    print('Encode: {:.2f}s'.format(encode_time-align_time))
    print('Predict: {:.2f}s'.format(finished_time-encode_time))
    print('Total: {:.2f}s'.format(finished_time-start_time))

    return integrate_json(final_result)


@api_router.post("/encode")
async def encode_endpoint(image: ImageRequest):
    img = readb64(image.img)
    aligned_img = face_align_crop(_cropper_model, img, _device)
    return {"encodings": encode(_models, 'cpu', aligned_img).to_dict()}


@api_router.post("/crop")
async def crop_endpoint(image: ImageRequest):
    img = readb64(image.img)
    aligned_img = face_align_crop(_cropper_model, img, _device)
    img_en = cv2.imencode(".png", aligned_img)
    return {"crop": base64.b64encode(img_en[1])}


@api_router.get("/status")
async def status_endpoint():
    return {"status": "running"}


app.include_router(api_router)


# --- Configuration for serving the Vue.js frontend ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/assets", 
          StaticFiles(directory=os.path.join(STATIC_DIR, "assets"))
          , name="static-assets",
          )
@app.get("/{full_path:path}")
async def serve_vue_app(full_path: str):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

