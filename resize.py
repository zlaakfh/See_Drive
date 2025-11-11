import os
import glob
from PIL import Image
import sys

# --- 설정 (Configuration) ---

# 1. 원본 이미지 크기 (비율 계산용)
# 원본 크기가 이미지마다 다를 경우, 
# 아래 로직 대신 "스크립트 실행" 부분의 주석을 참고하세요.
ORIGINAL_SIZE = (4056, 3040) 

# 2. 목표 세로 크기 (Height)
TARGET_HEIGHT = 640

# 3. 새 이미지 크기 자동 계산 (비율 유지)
# 원본 비율 = 너비 / 높이
aspect_ratio = ORIGINAL_SIZE[0] / ORIGINAL_SIZE[1]
# 새 너비 = 목표 높이 * 비율 (정수로 반올림)
new_width = int(round(TARGET_HEIGHT * aspect_ratio))

# 최종적으로 계산된 새 크기 (e.g., (854, 640))
NEW_SIZE = (new_width, TARGET_HEIGHT)

# 4. 원본 데이터가 있는 기본 경로
BASE_PATH = './data'

# 5. 리사이즈된 이미지를 저장할 새 폴더 경로
OUTPUT_PATH = './data_resized'

# 6. 처리할 하위 폴더 목록
PARTITIONS = ['train', 'valid', 'test']

# 7. 이미지 형식 (png, jpg 등)
IMAGE_EXTENSION = 'png'

# --- 스크립트 시작 ---

def resize_images():
    print(f"이미지 리사이즈 시작... (목표 높이: {TARGET_HEIGHT}px)")
    print(f"원본 비율({ORIGINAL_SIZE[0]}:{ORIGINAL_SIZE[1]})에 맞춰 계산된 새 크기: {NEW_SIZE}")
    print(f"결과 저장 위치: {OUTPUT_PATH}\n")
    
    total_files = 0
    processed_files = 0

    try:
        for part in PARTITIONS:
            image_dir = os.path.join(BASE_PATH, part, 'image')
            output_dir = os.path.join(OUTPUT_PATH, part, 'image')
            os.makedirs(output_dir, exist_ok=True)
            
            print(f"--- [{part}] 폴더 처리 중 ---")
            print(f"원본 위치: {image_dir}")

            image_files = glob.glob(os.path.join(image_dir, f'*.{IMAGE_EXTENSION}'))
            
            if not image_files:
                print(f"경고: '{image_dir}'에서 '*.{IMAGE_EXTENSION}' 파일을 찾을 수 없습니다.\n")
                continue

            total_files += len(image_files)

            for img_path in image_files:
                try:
                    with Image.open(img_path) as img:
                                               
                        # 이미지 리사이즈 (LANCZOS는 고품질 축소 필터)
                        img_resized = img.resize(NEW_SIZE, Image.LANCZOS)
                        
                        filename = os.path.basename(img_path)
                        new_img_path = os.path.join(output_dir, filename)
                        
                        img_resized.save(new_img_path)
                        processed_files += 1

                except Exception as e:
                    print(f"오류: {img_path} 처리 중 문제 발생: {e}")

            print(f"[{part}] 폴더 처리 완료: {len(image_files)}개 파일 처리\n")

        print("--- 모든 작업 완료 ---")
        print(f"총 {total_files}개 파일 중 {processed_files}개를 성공적으로 처리했습니다.")

    except FileNotFoundError:
        print(f"오류: 원본 폴더 '{BASE_PATH}'를 찾을 수 없습니다.")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")

# 스크립트 실행
if __name__ == "__main__":
    resize_images()