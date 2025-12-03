

# 환경 구성

``` shell
# 가상 환경 생성 (선택 사항)
python -m venv detectron_env
source detectron_env/bin/activate  # Linux/macOS
# .\detectron_env\Scripts\activate # Windows

# 자신에 맞는 cuda 버전으로 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install --upgrade pip setuptools wheel

git clone https://github.com/facebookresearch/detectron2.git
cd detectron2
pip install --no-build-isolation  .
```

# 모델 학습
``` shell
python train.py
```

# 동영상 시각화
``` shell
python demo.py --config-file mask_rcnn_R_50_FPN_3x_4.yaml --video-input sample.mp4 --output output.mp4 --opts MODEL.WEIGHTS model.pth
```
