import os
import random
import cv2
import matplotlib.pyplot as plt

import detectron2
from detectron2.utils.logger import setup_logger
import logging
logger = setup_logger()

from detectron2.engine import DefaultTrainer, DefaultPredictor
from detectron2.config import get_cfg
from detectron2 import model_zoo

from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data.datasets import register_coco_instances

from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader
from detectron2.utils.visualizer import Visualizer, ColorMode
import detectron2
from detectron2.engine import DefaultTrainer
from detectron2.evaluation import COCOEvaluator
from detectron2.utils.logger import setup_logger
import logging



######################################################################
# ---------------------------------------------------------
# 🔧 0. 사용자 설정 
# ---------------------------------------------------------
# 이미지 가로 세로 크기
IMG_W = 1008
IMG_H = 760
# 클래스 개수
CLASS_NUM  = 4
# 학습 iter  
ITER_NUM   = 10000      
BATCH_SIZE = 16    # GPU 1대 기준 배치 사이즈   
######################################################################

# 16 batch 기준 레퍼런스 LR
BASE_LR_REF = 0.02         
# 이미지 사이즈
IMG_SIZE   = f"{IMG_W}x{IMG_H}"
# 데이터셋 이름 (split/transform 코드와 동일 포맷)
DATASET_NAME = f"dataset_DT_cls{CLASS_NUM}_{IMG_SIZE}"

# 학습 이름 (output/log/weight 이름에 사용)
TRAIN_NAME = f"DT_cls{CLASS_NUM}_{IMG_SIZE}_iter{ITER_NUM}"

# COCO json & image 경로 (train/val/test 공통 prefix)
DATASET_ROOT = f"/home/elicer/train_data_split/{DATASET_NAME}"

# 출력 루트
OUTPUT_ROOT = "/home/elicer/Workspace/trained_output/output"
# 원하는 로그 경로 설정
# 1) 기본 detectron2 로거(학습 출력은 콘솔에만): 파일 로깅 없음
setup_logger()

# 2) 평가 로그만 저장할 폴더/파일
LOG_DIR = f"/home/elicer/Workspace/train_log/{TRAIN_NAME}"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "eval.log")   # <- 평가 로그만 저장될 파일 이름

# 3) Detectron2 평가(evaluation) 전용 로거 가져오기
eval_logger = logging.getLogger("detectron2.evaluation")
eval_logger.setLevel(logging.INFO)

# 4) 파일 핸들러 생성
eval_file_handler = logging.FileHandler(LOG_PATH)
eval_file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

# 5) 평가 로거에만 파일 핸들러 추가 (학습 로그는 안 들어감)
eval_logger.addHandler(eval_file_handler)

# 6) 평가 로그 상위 전파 막기(중복 방지)
eval_logger.propagate = False
# ---------------------------------------------------------
# 1. 데이터셋 등록 함수
# ---------------------------------------------------------


class MyTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg, dataset_name, output_folder=None):
        # 훈련 중간/마지막에 사용할 evaluator 정의
        if output_folder is None:
            output_folder = os.path.join(cfg.OUTPUT_DIR, "inference", dataset_name)
        os.makedirs(output_folder, exist_ok=True)
        return COCOEvaluator(dataset_name, output_dir=output_folder)


def register_datasets():
    """
    train / val / test COCO 데이터셋 등록.
    실행 위치 기준으로 ./dataset_... 경로 사용.
    """
    train_json = os.path.join(DATASET_ROOT, "train.json")
    val_json   = os.path.join(DATASET_ROOT, "val.json")
    test_json  = os.path.join(DATASET_ROOT, "test.json")

    train_img_dir = os.path.join(DATASET_ROOT, "train/images")
    val_img_dir   = os.path.join(DATASET_ROOT, "val/images")
    test_img_dir  = os.path.join(DATASET_ROOT, "test/images")

    register_coco_instances("train_parking", {}, train_json, train_img_dir)
    register_coco_instances("val_parking",   {}, val_json,   val_img_dir)
    register_coco_instances("test_parking",  {}, test_json,  test_img_dir)

    val_metadata = MetadataCatalog.get("val_parking")
    return val_metadata


# ---------------------------------------------------------
# 2. cfg 설정 함수
# ---------------------------------------------------------
def build_cfg():
    """
    학습/평가에 사용할 cfg 생성.
    """
    cfg = get_cfg()

    # 커스텀 이름 지정
    cfg.TRAIN_NAME = TRAIN_NAME
    cfg.OUTPUT_DIR = os.path.join(OUTPUT_ROOT, cfg.TRAIN_NAME)

    # config & pretrained weight 백본 통일 (R_50_FPN_3x)
    cfg.merge_from_file(
        "/home/elicer/sechan/detectron/detectron2_repo/configs/COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    )

    # 데이터셋 이름 설정
    cfg.DATASETS.TRAIN = ("train_parking",)
    cfg.DATASETS.TEST  = ("val_parking",)

    # DataLoader
    cfg.DATALOADER.NUM_WORKERS = 2

    # Pretrained weight
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    )

    # Batch & LR 설정
    num_gpu = 1
    per_gpu_batch = BATCH_SIZE
    cfg.SOLVER.IMS_PER_BATCH = num_gpu * per_gpu_batch

    # 16 batch 기준 BASE_LR_REF에서 선형 스케일
    cfg.SOLVER.BASE_LR = BASE_LR_REF * cfg.SOLVER.IMS_PER_BATCH / 16

    # 학습 스케줄
    cfg.SOLVER.MAX_ITER = ITER_NUM
    cfg.TEST.EVAL_PERIOD = 100
    cfg.SOLVER.CHECKPOINT_PERIOD = 1000
    # ROI Head 설정
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 128
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = CLASS_NUM

    # 디바이스
    cfg.MODEL.DEVICE = "cuda"   # 필요 시 "cpu"

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    return cfg


# ---------------------------------------------------------
# 3. 학습 함수
# ---------------------------------------------------------
def train_model(cfg):
    """
    MyTrainer(커스텀 Trainer)를 이용해 학습 수행.
    """
    trainer = MyTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()
    trainer.checkpointer.save(cfg.TRAIN_NAME)
    return trainer


# ---------------------------------------------------------
# 4. val 이미지 몇 장 시각화 함수 (옵션)
# ---------------------------------------------------------
def visualize_val_samples(cfg, val_metadata, num_samples=3):
    """
    val_parking 데이터셋에서 몇 장 뽑아 시각화.
    """
    dataset_dicts = DatasetCatalog.get("val_parking")
    if len(dataset_dicts) == 0:
        print("No samples in val_parking to visualize.")
        return

    predictor = DefaultPredictor(cfg)

    for d in random.sample(dataset_dicts, min(num_samples, len(dataset_dicts))):
        img = cv2.imread(d["file_name"])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        outputs = predictor(img)

        v = Visualizer(
            img,
            metadata=val_metadata,
            scale=0.5,
            instance_mode=ColorMode.IMAGE
        )
        out = v.draw_instance_predictions(outputs["instances"].to("cpu"))

        plt.figure(figsize=(8, 6))
        plt.imshow(out.get_image())
        plt.axis("off")
        plt.title(os.path.basename(d["file_name"]))
        plt.show()


# ---------------------------------------------------------
# 5. COCO 평가 함수 (val/test 공용)
# ---------------------------------------------------------
def evaluate_on_dataset(cfg, dataset_name, output_dir):
    """
    주어진 dataset_name에 대해 COCOEvaluator로 mAP 평가.
    """
    os.makedirs(output_dir, exist_ok=True)

    predictor = DefaultPredictor(cfg)

    evaluator = COCOEvaluator(dataset_name, output_dir=output_dir)
    data_loader = build_detection_test_loader(cfg, dataset_name)

    print(f"Running COCO evaluation on {dataset_name} ...")
    results = inference_on_dataset(predictor.model, data_loader, evaluator)
    print(f"COCO evaluation results for {dataset_name}:", results)
    return results


# ---------------------------------------------------------
# 6. main: 전체 실행 흐름
# ---------------------------------------------------------
def main():
    # 1) 데이터셋 등록
    val_metadata = register_datasets()

    # 2) cfg 구성
    cfg = build_cfg()

    # 3) 학습
    train_model(cfg)

    # 4) 학습된 모델 weight로 cfg 업데이트
    #    (trainer가 저장하는 최종 weight 이름이 아래와 동일하도록 맞춰줘야 함)
    final_weight_path = os.path.join(cfg.OUTPUT_DIR, f"{TRAIN_NAME}.pth")
    cfg.MODEL.WEIGHTS = final_weight_path
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7

    # 5) (옵션) val 이미지 시각화
    visualize_val_samples(cfg, val_metadata, num_samples=3)

    # 6) test_parking 평가
    inference_out_dir = os.path.join(OUTPUT_ROOT, "inference", cfg.TRAIN_NAME, "test")
    evaluate_on_dataset(cfg, "test_parking", inference_out_dir)

    # 7) TensorBoard 안내
    print("\n[TensorBoard 안내]")
    print(f"  로그 디렉토리: {cfg.OUTPUT_DIR}")
    print(f"  명령어: tensorboard --logdir {cfg.OUTPUT_DIR} --port 6006")


if __name__ == "__main__":
    main()

# tensorboard --logdir ./output/DT_cls6_2016x1520_iter1000 --port 6006
