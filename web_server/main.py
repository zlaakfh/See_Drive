from fastapi import FastAPI, File, UploadFile, Form, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Union, Any 
import shutil
import json
from pydantic import BaseModel, Field
from datetime import datetime
import datetime
from ultralytics import YOLO
from PIL import Image
import numpy as np
import io

FACE_DET_MODEL_PATH = "./model/yolov11n-face.pt"

# init_model
face_model = YOLO(FACE_DET_MODEL_PATH);


def _detect_boxes(model: YOLO, frame_bgr: np.ndarray, conf: float, iou: float, imgsz: int) -> np.ndarray:
    r = model.predict(frame_bgr, conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]
    return r.boxes.xyxy.detach().cpu().numpy() if r and r.boxes is not None and len(r.boxes) > 0 else np.empty((0,4), float)

app = FastAPI()


templates = Jinja2Templates(directory="templates")


app = FastAPI()

@app.get("/", summary="HTML 템플릿 렌더링")
async def serve_html_file(request: Request):
    
    # 템플릿에 전달할 동적 데이터 준비
    context_data = {
        "title": "동적 HTML 페이지",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # templates.TemplateResponse를 사용하여 HTML 파일(index.html)을 렌더링하고 반환
    # 'request': request는 Jinja2Templates 사용 시 필수입니다.
    # **context_data는 동적 데이터를 context에 추가합니다.
    return templates.TemplateResponse(
        name="index.html", 
        context={"request": request, **context_data}
    )

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    # 파일 처리 로직
    return {"filename": file.filename, "content_type": file.content_type}


# @app.post("/uploadfile/save")
# async def save_upload_file(file: UploadFile = File(...)):
#     # 저장할 경로 지정
#     file_location = f"files/{file.filename}"
    
#     # 파일을 동기적으로 저장 (shutil 사용)
#     # UploadFile의 file 속성은 파일 포인터입니다.
#     with open(file_location, "wb") as buffer:
#         # 파일을 비동기적으로 읽어 동기적으로 저장
#         shutil.copyfileobj(file.file, buffer)

#     return {"info": f"file saved at {file_location}"}

class AccelData(BaseModel):
    x: str
    y: str
    z: str
    magnitude: str

class GyroData(BaseModel):
    x: str
    y: str
    z: str

class GpsData(BaseModel):
    latitude: str
    longitude: str
    accuracy: str


class Metadata(BaseModel):
    """전체 센서 및 GPS 메타데이터 모델"""
    timestamp: str = Field(..., description="임계값 초과 감지 시점의 ISO 8601 시간")
    accel: AccelData
    gyro: GyroData
    # GPS 데이터가 없거나 (status: 'Location unavailable') 있을 경우를 처리
    gps: Dict[str, Any] # GpsData 또는 {'status': ...}를 유연하게 받기 위해 Dict[str, Any] 사용
    threshold_passed: bool

@app.post("/report")
async def create_upload_file(
    file: UploadFile = File(...), 
    metadata: str = Form(...) 
):
    """
    단일 이미지 파일과 JSON 메타데이터를 받아 처리하는 엔드포인트
    """
    now = datetime.datetime.now()
    formatted_time = now.strftime("%Y%m%d_%H%M%S")
    file_location = f"files/{formatted_time}_{file.filename}"
    # 1. 파일 처리 및 저장
    try:
        # 파일을 동기적으로 디스크에 저장
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    except Exception:
        # 파일 저장 실패 시 500 에러 반환
        raise HTTPException(status_code=500, detail="파일 저장에 실패했습니다.")
    finally:
        # 임시 파일을 닫아 리소스 해제
        await file.close()

    # 2. 메타데이터 (JSON 문자열) 파싱 및 유효성 검사
    metadata_data = None
    try:
        # 문자열로 받은 metadata를 JSON으로 파싱
        json_data = json.loads(metadata)
        # 파싱된 JSON 데이터를 Pydantic 모델로 검증 (선택 사항)
        metadata_data = Metadata(**json_data)
        
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 400 에러 반환
        raise HTTPException(status_code=400, detail="제공된 메타데이터가 유효한 JSON 형식이 아닙니다.")
    except Exception as e:
        # Pydantic 유효성 검사 실패 등 기타 에러
        raise HTTPException(status_code=400, detail=f"메타데이터 유효성 검사 실패: {e}")

    print(json_data)

    # 3. 최종 응답
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "file_location": file_location,
        "metadata_received": metadata_data.model_dump() if metadata_data else json_data, # Pydantic 객체 또는 파싱된 JSON 반환
        "message": "파일과 메타데이터가 성공적으로 저장 및 처리되었습니다."
    }