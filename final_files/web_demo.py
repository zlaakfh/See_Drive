import cv2
import numpy as np
import math
from dataclasses import dataclass
import threading
import time
from flask import Flask, Response, request, jsonify

# =========================
# 설정
# =========================
USE_DUMMY_SLOTS = False  # True면 더미 슬롯, False면 Detectron2 사용  # 웹캠, 동영상 파일, 네트워크카메라 주소
VIDEO_SOURCE = "/home/elicer/junlee/back_parking/videos05/15fps/front01_15fps.mp4"
BACK_VIDEO_SOURCE = "/home/elicer/junlee/back_parking/videos05/30fps/back01_part1_30fps_v3.mp4"
THIRD_VIDEO_SOURCE = "/home/elicer/junlee/back_parking/videos05/15fps/back_final.MOV"

FRAME_W = 1280
FRAME_H = 720

# Detectron2 설정 (환경에 맞게 수정)
DETECTRON_CFG_FILE = "/home/elicer/sechan/detectron/detectron2_repo/configs/COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
DETECTRON_WEIGHTS  = "/home/elicer/jaehyun/new_parking_trained_output/output/new_parking_DT_cls2_1920x1080_iter100000/model_0079999.pth"
DETECTRON_DEVICE   = "cuda"   # "cuda" 또는 "cpu"

PARKING_CLASS_ID = 1   # Parking Area 클래스 ID
MIN_SLOT_AREA    = 300 # 너무 작은 마스크는 무시

# Detectron2를 N프레임마다 한 번만 실행
DETECT_EVERY_N_FRAMES = 3

# 전역 상태 (스트리밍용)
total_frames = 0      # 전체 프레임 수
video_frame_idx = 0   # 지금까지 재생한 프레임 인덱스

# ★ GO_FORWARD 진행 상황(프레임 기준)
go_frames_since = 0    # confirm 이후 지금까지 재생된 프레임 수
go_frames_total = None # 영상이 끝날 때 확정되는 총 프레임 수

EXACT_TOTAL_FRAMES = None
BACK_EXACT_TOTAL_FRAMES = None
THIRD_EXACT_TOTAL_FRAMES = None

in_third_video = False

# 후진 슬롯 트래킹 허용 최대 이동 거리(픽셀)
BACK_TRACK_MAX_DIST = 120  # 필요하면 80~150 정도로 조정
BACK_TRACK_MAX_DIST2 = BACK_TRACK_MAX_DIST ** 2

# =========================
# 데이터 구조
# =========================
@dataclass
class ParkingSlot:
    slot_id: int
    polygon: np.ndarray  # (N,2) int32
    center: tuple        # (x, y)


@dataclass
class CarPose:
    x: float
    y: float
    yaw: float           # 라디안
    reverse: bool = False  # 후진 구간 여부


def get_initial_car_pose() -> CarPose:
    """항상 내 시점(화면 아래 중앙, 위쪽을 바라보는 자세)에서 시작"""
    return CarPose(FRAME_W // 2, int(FRAME_H * 0.90), -math.pi / 2)


def get_exact_frame_count(video_path: str) -> int:
    cap = cv2.VideoCapture(video_path)
    cnt = 0
    while True:
        ret, _ = cap.read()
        if not ret:
            break
        cnt += 1
    cap.release()
    print(f"[INFO] exact frame count for {video_path} = {cnt}")
    return cnt


EXACT_TOTAL_FRAMES = get_exact_frame_count(VIDEO_SOURCE)
BACK_EXACT_TOTAL_FRAMES = get_exact_frame_count(BACK_VIDEO_SOURCE)
THIRD_EXACT_TOTAL_FRAMES = get_exact_frame_count(THIRD_VIDEO_SOURCE)

# =========================
# Detectron2 ParkingSlot Detector
# =========================
class ParkingDetector:
    def __init__(self, use_dummy=True):
        self.use_dummy = use_dummy
        self.slot_id_counter = 0

        if not use_dummy:
            from detectron2.config import get_cfg
            from detectron2.engine import DefaultPredictor

            cfg = get_cfg()
            cfg.merge_from_file(DETECTRON_CFG_FILE)
            cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2
            cfg.MODEL.WEIGHTS = DETECTRON_WEIGHTS
            cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
            cfg.MODEL.DEVICE = DETECTRON_DEVICE
            self.predictor = DefaultPredictor(cfg)
        else:
            self.predictor = None

    def detect(self, frame):
        if self.use_dummy:
            return self._dummy_slots(frame)
        return self._detectron_slots(frame)

    def _dummy_slots(self, frame):
        h, w, _ = frame.shape
        rects = [
            [(int(w * 0.60), int(h * 0.60)), (int(w * 0.80), int(h * 0.70))],
            [(int(w * 0.20), int(h * 0.50)), (int(w * 0.40), int(h * 0.60))],
            [(int(w * 0.45), int(h * 0.40)), (int(w * 0.65), int(h * 0.50))],
        ]
        slots = []
        self.slot_id_counter = 0
        for (x1, y1), (x2, y2) in rects:
            poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            self.slot_id_counter += 1
            slots.append(ParkingSlot(self.slot_id_counter, poly, (cx, cy)))
        return slots

    def _detectron_slots(self, frame):
        outputs = self.predictor(frame)
        instances = outputs["instances"].to("cpu")

        if not instances.has("pred_masks"):
            return []

        masks = instances.pred_masks.numpy()        # (N, H, W)
        classes = instances.pred_classes.numpy()    # (N,)

        slots = []
        self.slot_id_counter = 0

        for mask, cid in zip(masks, classes):
            if PARKING_CLASS_ID is not None and cid != PARKING_CLASS_ID:
                continue

            mask_u8 = (mask.astype(np.uint8) * 255)
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue

            cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(cnt)
            if area < MIN_SLOT_AREA:
                continue

            poly = cnt.reshape(-1, 2).astype(np.int32)

            cx = int(poly[:, 0].mean())
            cy = int(poly[:, 1].mean())

            self.slot_id_counter += 1
            slots.append(ParkingSlot(self.slot_id_counter, poly, (cx, cy)))

        return slots


# =========================
# Slot Selector
# =========================
class SlotSelector:
    def __init__(self):
        self.slots = []
        self.selected_slot_id = None

    def update(self, slots):
        self.slots = slots

    def click(self, x, y):
        clicked = False
        for slot in self.slots:
            if cv2.pointPolygonTest(slot.polygon, (x, y), False) >= 0:
                self.selected_slot_id = slot.slot_id
                clicked = True
                print("[INFO] 슬롯 선택:", slot.slot_id)
                break
        if not clicked:
            print("[INFO] 빈 공간 클릭 → 선택 해제")
            self.selected_slot_id = None

    def get(self):
        if self.selected_slot_id is None:
            return None
        for s in self.slots:
            if s.slot_id == self.selected_slot_id:
                return s
        return None

    def clear(self):
        self.selected_slot_id = None


# =========================
# Parking Planner (T자 후진)
# =========================
class ParkingPlanner:
    def __init__(self):
        self.path = []

    @staticmethod
    def _angle_diff(a, b):
        return ((a - b + math.pi) % (2 * math.pi)) - math.pi

    def plan(self, start_pose: CarPose, slot: ParkingSlot):
        mid_x = FRAME_W / 2
        if slot.center[0] <= mid_x:
            self.path = self._plan_left(start_pose, slot)
            return self.path
        else:
            start_m = self._mirror_pose(start_pose)
            slot_m = self._mirror_slot(slot)
            path_m = self._plan_left(start_m, slot_m)
            self.path = [self._mirror_pose(p) for p in path_m]
            return self.path

    @staticmethod
    def _mirror_pose(p: CarPose) -> CarPose:
        x_m = FRAME_W - p.x
        y_m = p.y
        yaw_m = math.pi - p.yaw
        yaw_m = ((yaw_m + math.pi) % (2 * math.pi)) - math.pi
        return CarPose(x_m, y_m, yaw_m, reverse=p.reverse)

    @staticmethod
    def _mirror_slot(s: ParkingSlot) -> ParkingSlot:
        poly = s.polygon.astype(float)
        poly[:, 0] = FRAME_W - poly[:, 0]
        cx = FRAME_W - s.center[0]
        cy = s.center[1]
        return ParkingSlot(s.slot_id, poly.astype(np.int32), (int(cx), int(cy)))

    def _plan_left(self, start_pose: CarPose, slot: ParkingSlot):
        cx, cy = slot.center
        lane_yaw = start_pose.yaw
        lane_dir = np.array([math.cos(lane_yaw), math.sin(lane_yaw)], dtype=np.float32)

        pts = slot.polygon.reshape(-1, 2).astype(np.float32)
        mean = pts.mean(axis=0, keepdims=True)
        pts_c = pts - mean
        cov = np.cov(pts_c.T)
        eigvals, eigvecs = np.linalg.eig(cov)
        main_vec = eigvecs[:, np.argmax(eigvals)]
        slot_yaw_raw = math.atan2(main_vec[1], main_vec[0])
        slot_yaw_raw = ((slot_yaw_raw + math.pi) % (2 * math.pi)) - math.pi

        cand0 = lane_yaw
        cand1 = ((lane_yaw + math.pi / 2) + math.pi) % (2 * math.pi) - math.pi
        cand2 = ((lane_yaw - math.pi / 2) + math.pi) % (2 * math.pi) - math.pi
        candidates = [cand0, cand1, cand2]

        best_yaw = cand0
        best_diff = abs(self._angle_diff(slot_yaw_raw, cand0))
        for c in candidates[1:]:
            d = abs(self._angle_diff(slot_yaw_raw, c))
            if d < best_diff:
                best_diff = d
                best_yaw = c

        slot_yaw = best_yaw
        park_pose = CarPose(cx, cy, slot_yaw, reverse=True)

        vec_to_slot = np.array([cx - start_pose.x, cy - start_pose.y], dtype=np.float32)
        proj_dist = float(np.dot(vec_to_slot, lane_dir))
        if proj_dist < 0:
            proj_dist = 0.0

        margin = 120.0
        forward_dist = proj_dist + margin

        fx = start_pose.x + lane_dir[0] * forward_dist
        fy = start_pose.y + lane_dir[1] * forward_dist
        lane_forward_pose = CarPose(fx, fy, lane_yaw, reverse=False)

        forward_path = self._straight_forward(start_pose, lane_forward_pose, steps=60)
        reverse_path = self._reverse_curve_then_straight_from_lane(
            lane_forward_pose,
            park_pose,
            slot_yaw,
            slot.center,
            total_steps=110,
        )

        return forward_path + reverse_path

    @staticmethod
    def _straight_forward(p0: CarPose, p1: CarPose, steps=60):
        if steps < 2:
            steps = 2

        path = []
        for i in range(steps):
            t = i / (steps - 1)
            x = p0.x * (1 - t) + p1.x * t
            y = p0.y * (1 - t) + p1.y * t
            yaw = p0.yaw
            path.append(CarPose(x, y, yaw, reverse=False))
        return path

    def _reverse_curve_then_straight_from_lane(
        self,
        start_pose: CarPose,
        park_pose: CarPose,
        slot_yaw: float,
        slot_center: tuple,
        total_steps=110,
    ):
        curve_ratio = 0.6
        curve_steps = max(2, int(total_steps * curve_ratio))
        straight_steps = max(1, total_steps - curve_steps)

        front_offset = 190.0
        mx = park_pose.x + front_offset * math.cos(slot_yaw)
        my = park_pose.y + front_offset * math.sin(slot_yaw)
        mid_pose = CarPose(mx, my, slot_yaw, reverse=True)

        p0v = np.array([start_pose.x, start_pose.y], dtype=np.float32)
        p2v = np.array([mid_pose.x, mid_pose.y], dtype=np.float32)
        scv = np.array([slot_center[0], slot_center[1]], dtype=np.float32)

        base = p2v - p0v
        base_norm = np.linalg.norm(base)
        if base_norm < 1e-5:
            base = np.array([1.0, 0.0], dtype=np.float32)
            base_norm = 1.0
        base_dir = base / base_norm

        to_slot = scv - p0v
        cross = base_dir[0] * to_slot[1] - base_dir[1] * to_slot[0]

        left_normal = np.array([-base_dir[1], base_dir[0]])
        curve_side_offset = 80.0
        if cross >= 0:
            shift = -left_normal * curve_side_offset
        else:
            shift = left_normal * curve_side_offset

        mid_line = 0.5 * (p0v + p2v)
        p1v = mid_line + shift

        bezier_positions = []
        for i in range(curve_steps):
            t = i / (curve_steps - 1)
            one_t = 1.0 - t
            pos = (one_t * one_t) * p0v + 2.0 * one_t * t * p1v + (t * t) * p2v
            bezier_positions.append(pos)

        path = []
        lane_yaw = start_pose.yaw
        for i in range(curve_steps):
            t = i / (curve_steps - 1)
            x, y = bezier_positions[i]
            yaw = self._smooth_yaw(lane_yaw, slot_yaw, t)
            path.append(CarPose(float(x), float(y), yaw, reverse=True))

        sx, sy = path[-1].x, path[-1].y
        for i in range(1, straight_steps + 1):
            t = i / straight_steps
            x = sx * (1 - t) + park_pose.x * t
            y = sy * (1 - t) + park_pose.y * t
            yaw = slot_yaw
            path.append(CarPose(x, y, yaw, reverse=True))

        return path

    @staticmethod
    def _smooth_yaw(y0, y1, t):
        t2 = t * t * (3 - 2 * t)
        dy = ((y1 - y0 + math.pi) % (2 * math.pi)) - math.pi
        return y0 + dy * t2


# =========================
# Path Follower
# =========================
class PathFollower:
    def __init__(self):
        self.path = []
        self.idx = 0
        self.active = False

    def start(self, path):
        self.path = path
        self.idx = 0
        self.active = True

    def step(self):
        if not self.active or self.idx >= len(self.path):
            self.active = False
            return None
        p = self.path[self.idx]
        self.idx += 1
        return p


# =========================
# path 리샘플링 (후진 BEV용)
# =========================
def resample_path(path_in, steps):
    if not path_in:
        return []

    n = len(path_in)
    if steps <= 1 or n == 1:
        p = path_in[-1]
        return [CarPose(p.x, p.y, p.yaw, reverse=True)]

    out = []
    for i in range(steps):
        t = i / (steps - 1)
        f = t * (n - 1)
        i0 = int(math.floor(f))
        i1 = min(i0 + 1, n - 1)
        alpha = f - i0

        p0 = path_in[i0]
        p1 = path_in[i1]

        x = p0.x * (1 - alpha) + p1.x * alpha
        y = p0.y * (1 - alpha) + p1.y * alpha
        yaw = ParkingPlanner._smooth_yaw(p0.yaw, p1.yaw, alpha)

        out.append(CarPose(x, y, yaw, reverse=True))
    return out


# =========================
# BEV Renderer
# =========================
class BEVRenderer:
    def __init__(self, w=600, h=600):
        self.w = w
        self.h = h

    def render(self, slots, car_pose, path, slam_goal=None):
        bev = np.zeros((self.h, self.w, 3), np.uint8)
        sx = self.w / FRAME_W
        sy = self.h / FRAME_H

        if path:
            pts = np.array([[int(p.x * sx), int(p.y * sy)] for p in path], np.int32)
            cv2.polylines(bev, [pts], False, (255, 255, 255), 1)

        for s in slots:
            poly = s.polygon.astype(float)
            poly[:, 0] *= sx
            poly[:, 1] *= sy
            cv2.polylines(bev, [poly.astype(int)], True, (0, 255, 0), 2)

        if car_pose:
            cx = int(car_pose.x * sx)
            cy = int(car_pose.y * sy)
            car_len = 40
            car_wid = 20
            rect = np.array([
                [-car_len / 2, -car_wid / 2],
                [ car_len / 2, -car_wid / 2],
                [ car_len / 2,  car_wid / 2],
                [-car_len / 2,  car_wid / 2],
            ], dtype=np.float32)
            R = np.array([
                [math.cos(car_pose.yaw), -math.sin(car_pose.yaw)],
                [math.sin(car_pose.yaw),  math.cos(car_pose.yaw)],
            ])
            rect = (R @ rect.T).T
            rect[:, 0] += cx
            rect[:, 1] += cy
            rect = rect.astype(np.int32)
            cv2.polylines(bev, [rect], True, (0, 0, 255), 2)

        if slam_goal is not None:
            gx = int(slam_goal["x"] * sx)
            gy = int(slam_goal["y"] * sy)
            cv2.circle(bev, (gx, gy), 6, (0, 0, 255), -1)

        cv2.putText(bev, "BEV", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return bev


# =========================
# FrontView Car 렌더링
# =========================
def draw_car_front(img, p: CarPose):
    car_len = 70
    car_wid = 35
    cx, cy = int(p.x), int(p.y)

    rect = np.array([
        [-car_len / 2, -car_wid / 2],
        [ car_len / 2, -car_wid / 2],
        [ car_len / 2,  car_wid / 2],
        [-car_len / 2,  car_wid / 2],
    ], dtype=np.float32)

    R = np.array([
        [math.cos(p.yaw), -math.sin(p.yaw)],
        [math.sin(p.yaw),  math.cos(p.yaw)],
    ])
    rect = (R @ rect.T).T
    rect[:, 0] += cx
    rect[:, 1] += cy
    rect = rect.astype(np.int32)

    color = (0, 0, 255) if not p.reverse else (0, 255, 255)
    cv2.polylines(img, [rect], True, color, 3)

    driver_pt = rect[1]
    cv2.circle(img, tuple(driver_pt), 6, (0, 0, 255), -1)


# =========================
# 후진 영상용 곡선 가이드 생성
# =========================
def generate_back_curve(start_x, start_y, end_x, end_y, num_points=60):
    """
    화면 중앙 하단(p0)에서 시작해서 슬롯(center, p3)까지 가는 곡선.
    - p0 근처가 더 많이 휘고
    - p3(슬롯) 근처는 점점 곧게 붙도록 3차 베지어 사용.
    """
    p0 = np.array([float(start_x), float(start_y)], dtype=np.float32)
    p3 = np.array([float(end_x), float(end_y)], dtype=np.float32)

    # 전체 높이 차이 기준으로 오프셋 크기 결정
    dy = abs(p3[1] - p0[1])
    base_offset = max(140.0, dy * 0.8)

    # 제어점 1: 시작점 근처에 강하게 위로 당겨서 "아래쪽이 더 curvy"
    p1 = p0 + np.array([0.0, -base_offset], dtype=np.float32)

    # 제어점 2: 중간 쯤에서 살짝만 위로 (슬롯 쪽은 더 straight)
    mid = 0.5 * (p0 + p3)
    p2 = mid + np.array([0.0, -base_offset * 0.35], dtype=np.float32)

    pts = []
    for i in range(num_points):
        t = i / (num_points - 1)
        one_t = 1.0 - t
        # 3차 베지어: B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
        pos = (one_t**3) * p0 \
              + 3 * (one_t**2) * t * p1 \
              + 3 * one_t * (t**2) * p2 \
              + (t**3) * p3
        pts.append((int(pos[0]), int(pos[1])))

    return pts


# =========================
# 전역 상태 (스트리밍용)
# =========================
app = Flask(__name__)

state_lock = threading.Lock()

detector = ParkingDetector(USE_DUMMY_SLOTS)
selector = SlotSelector()
planner = ParkingPlanner()
follower = PathFollower()
bev_renderer = BEVRenderer()

car_pose = get_initial_car_pose()

freeze = False
freeze_frame = None
freeze_slots = []
slots = []
path = []
latest_raw_frame = None
front_view_frame = None
bev_frame = None

pending_click = None
pending_reset = False

slam_goal = None
confirmed = False

# ★ 추가: START 버튼 누르기 전에는 영상 고정
started = False

bev_static_slots = []
bev_static_path = []
bev_static_car_pose = None
bev_forward_segment = []

back_mode = False
reverse_path = []
reverse_idx  = 0

# 후진용 선 / 타깃
back_curve_pts = []
back_target_center = None
back_selected_slot_current = None


# =========================
# 백그라운드 처리 루프
# =========================
def processing_loop():
    global car_pose, freeze, freeze_frame, freeze_slots
    global slots, path, latest_raw_frame, front_view_frame, bev_frame
    global pending_click, pending_reset, slam_goal, confirmed
    global total_frames, video_frame_idx
    global bev_static_slots, bev_static_path, bev_static_car_pose, bev_forward_segment
    global go_frames_since, go_frames_total
    global EXACT_TOTAL_FRAMES, BACK_EXACT_TOTAL_FRAMES
    global back_mode, reverse_path, reverse_idx
    global back_curve_pts, back_target_center, back_selected_slot_current
    global started, cap_back2, in_third_video

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    cap_back = None
    cap_back2 = None
    in_third_video = False
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    frame_idx = 0
    total_frames = EXACT_TOTAL_FRAMES
    video_frame_idx = 0

    prev_time = time.time()
    fps = 0.0

    while True:
        with state_lock:
            # =========================
            # 1) START 이전: READY 화면
            # =========================
            if not started:
                # 아직 freeze_frame이 없으면 첫 프레임 한 장만 읽어서 고정 화면으로 사용
                if freeze_frame is None:
                    ret, frame = cap.read()
                    if not ret:
                        # 영상이 이상하면 잠깐 쉬었다 다시 시도
                        time.sleep(0.05)
                        continue
                    frame = cv2.resize(frame, (FRAME_W, FRAME_H))
                    latest_raw_frame = frame.copy()

                    # 첫 화면을 freeze_frame으로 저장
                    freeze_frame = frame.copy()
                    freeze_slots = []
                    slots = []
                    selector.update(slots)

                current = freeze_frame.copy()
                slots_to_draw = freeze_slots
                mode_text = "READY - Press START"

                # READY 화면에서도 차 위치는 화면 하단 중앙으로 그려주기
                car_pose = get_initial_car_pose()
                draw_car_front(current, car_pose)

                # 텍스트 + FPS 표시 (FPS는 0 근처일 것)
                cv2.putText(current, mode_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                            (0, 255, 255), 2, cv2.LINE_AA)
                fps_text = f"FPS: {fps:4.1f}"
                cv2.putText(current, fps_text, (FRAME_W - 220, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                            (0, 255, 0), 2, cv2.LINE_AA)

                # Front / BEV 프레임 갱신
                front_view_frame = current
                bev_frame = bev_renderer.render(slots_to_draw, car_pose, [], None)

            # =========================
            # 2) START 이후: 기존 로직 그대로
            # =========================
            else:
                if not freeze:
                    ret, frame = cap.read()

                    if not ret:
                        # ===== front 영상 끝 → back 전환 =====
                        if not back_mode:
                            if confirmed and path:
                                follower.idx = len(path)
                                car_pose = path[-1]

                            print("[INFO] front video ended → switch to BACK camera")
                            back_mode = True
                            confirmed = False
                            follower.active = False

                            if bev_static_path:
                                rev_segment = [p for p in bev_static_path if p.reverse]
                                if not rev_segment:
                                    rev_segment = list(bev_static_path)

                                # ★ back + third 두 영상 길이를 합쳐서 곡선 전체 길이로 사용
                                total_back_frames = (BACK_EXACT_TOTAL_FRAMES or 0) + (THIRD_EXACT_TOTAL_FRAMES or 0)
                                steps = max(2, total_back_frames)
                                reverse_path = resample_path(rev_segment, steps)
                            else:
                                total_back_frames = (BACK_EXACT_TOTAL_FRAMES or 0) + (THIRD_EXACT_TOTAL_FRAMES or 0)
                                steps = max(2, total_back_frames)
                                reverse_path = [
                                    CarPose(car_pose.x, car_pose.y, car_pose.yaw, reverse=True)
                                    for _ in range(steps)
                                ]
                            reverse_idx = 0

                            if cap_back is None:
                                cap_back = cv2.VideoCapture(BACK_VIDEO_SOURCE)
                                if not cap_back.isOpened():
                                    print("[WARN] cannot open BACK_VIDEO_SOURCE, keep last frame")
                                    if latest_raw_frame is not None:
                                        frame = latest_raw_frame.copy()
                                    else:
                                        time.sleep(0.05)
                                        continue
                                cap = cap_back
                                in_third_video=False

                            ret, frame = cap.read()
                            if not ret:
                                if latest_raw_frame is not None:
                                    frame = latest_raw_frame.copy()
                                else:
                                    time.sleep(0.05)
                                    continue

                            frame = cv2.resize(frame, (FRAME_W, FRAME_H))
                            latest_raw_frame = frame.copy()
                            video_frame_idx = 0

                            # 후진 첫 프레임에서 freeze + 슬롯 탐지
                            freeze = True
                            freeze_frame = frame.copy()

                            slots = detector.detect(frame)
                            freeze_slots = slots.copy()
                            selector.update(slots)

                            back_curve_pts = []
                            back_target_center = None
                            back_selected_slot_current = None

                        # ===== 후방 영상도 끝난 경우 =====
                        else:
                            # BACK_VIDEO_SOURCE 재생이 끝난 뒤에는 세 번째 영상으로 전환
                            if cap_back2 is None:
                                cap_back2 = cv2.VideoCapture(THIRD_VIDEO_SOURCE)
                                if not cap_back2.isOpened():
                                    print("[WARN] cannot open THIRD_VIDEO_SOURCE, keep last frame")
                                    if latest_raw_frame is not None:
                                        frame = latest_raw_frame.copy()
                                    else:
                                        time.sleep(0.05)
                                        continue
                                cap = cap_back2  # 이후 루프에서도 이 cap을 계속 사용
                                in_third_video = True

                            # 세 번째 영상에서 프레임 읽기
                            ret2, frame = cap.read()
                            if not ret2:
                                # 세 번째 영상까지 모두 끝났으면 마지막 프레임 유지
                                if latest_raw_frame is not None:
                                    frame = latest_raw_frame.copy()
                                else:
                                    time.sleep(0.05)
                                    continue
                            else:
                                frame = cv2.resize(frame, (FRAME_W, FRAME_H))
                                latest_raw_frame = frame.copy()
                    else:
                        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
                        latest_raw_frame = frame.copy()
                        video_frame_idx += 1

                    frame_idx += 1
                    if (not confirmed) and frame_idx % DETECT_EVERY_N_FRAMES == 0:
                        new_slots = detector.detect(frame)

                        # ===== 후진 모드에서 선택 슬롯을 "락" 하면서만 업데이트 =====
                        if back_mode and back_target_center is not None:
                            if new_slots:
                                tx, ty = back_target_center

                                # 1) 이전 타겟(center)에 가장 가까운 슬롯 찾기
                                best = min(
                                    new_slots,
                                    key=lambda s: (s.center[0] - tx) ** 2 + (s.center[1] - ty) ** 2
                                )
                                dist2 = (best.center[0] - tx) ** 2 + (best.center[1] - ty) ** 2

                                # 2) 일정 거리 이내면 "같은 슬롯"이라고 보고 업데이트
                                if (back_selected_slot_current is None) or (dist2 <= BACK_TRACK_MAX_DIST2):
                                    slots[:] = [best]
                                    back_target_center = best.center
                                    back_selected_slot_current = best
                                else:
                                    # 3) 너무 멀리 떨어진 슬롯이면 Detectron 결과 무시 → 이전 슬롯 유지
                                    if back_selected_slot_current is not None:
                                        slots[:] = [back_selected_slot_current]
                                    else:
                                        slots[:] = []
                            else:
                                # 4) 아예 Detectron이 아무 슬롯도 못 찾으면 이전 슬롯 그대로 유지
                                if back_selected_slot_current is not None:
                                    slots[:] = [back_selected_slot_current]
                                else:
                                    slots[:] = []
                        else:
                            # 일반 모드에서는 기존처럼 전체 업데이트
                            slots[:] = new_slots

                    selector.update(slots)
                    current = frame.copy()

                    if confirmed:
                        slots_to_draw = []
                        mode_text = "GO FORWARD"
                    elif back_mode:
                        if back_selected_slot_current is not None:
                            slots_to_draw = [back_selected_slot_current]
                        else:
                            slots_to_draw = slots
                        mode_text = "REVERSE (rear camera)"
                    else:
                        slots_to_draw = slots
                        mode_text = "SEARCH (click slot via /click, Reset via /reset)"
                else:
                    if freeze_frame is None:
                        freeze = False
                        continue
                    current = freeze_frame.copy()
                    slots_to_draw = freeze_slots
                    if back_mode:
                        mode_text = "REAR SELECT (click slot)"
                    else:
                        mode_text = "PARKING (Reset via /reset)"

                # 클릭 처리
                if pending_click is not None and (not confirmed or back_mode):
                    x, y = pending_click
                    pending_click = None
                    selector.click(x, y)
                    selected = selector.get()

                    if back_mode:
                        if selected is not None:
                            print("[INFO] BACK MODE: slot selected → start tracking")
                            back_target_center = selected.center
                            back_selected_slot_current = selected

                            slots = [selected]
                            freeze_slots = slots.copy()
                            selector.selected_slot_id = selected.slot_id

                            back_curve_pts = []
                            freeze = False
                        else:
                            print("[INFO] BACK MODE: empty click (no slot)")
                    else:
                        if selected is not None and not freeze:
                            print("[INFO] Freeze ON & Path Planning")
                            freeze = True
                            freeze_frame = current.copy()
                            freeze_slots = slots_to_draw.copy()

                            start_pose = get_initial_car_pose()
                            car_pose = start_pose

                            path = planner.plan(start_pose, selected)
                            follower.start(path)
                            slam_goal = None

                            bev_static_slots = freeze_slots.copy()
                            bev_static_path = path.copy()


                # reset 처리
                if pending_reset:
                    print("[INFO] Reset / Cancel parking (HTTP)")
                    pending_reset = False
                    freeze = False
                    selector.clear()
                    follower.active = False
                    path = []
                    car_pose = get_initial_car_pose()
                    slam_goal = None
                    confirmed = False

                    bev_static_slots = []
                    bev_static_path = []
                    bev_static_car_pose = None
                    bev_forward_segment = []

                    back_mode = False
                    reverse_path = []
                    reverse_idx = 0
                    back_curve_pts = []
                    back_target_center = None
                    back_selected_slot_current = None

                if follower.active:
                    new_pose = follower.step()
                    if new_pose is not None:
                        car_pose = new_pose

                now = time.time()
                dt = now - prev_time
                prev_time = now
                if dt > 0:
                    inst_fps = 1.0 / dt
                    fps = fps * 0.9 + inst_fps * 0.1

                # ===== FrontView 렌더링 =====
                overlay = current.copy()

                if not confirmed and not (back_mode and not freeze):
                    selected = selector.get()
                    for s in slots_to_draw:
                        col = (0, 255, 0)
                        if selected is not None and s.slot_id == selected.slot_id:
                            col = (0, 255, 255)
                        cv2.polylines(overlay, [s.polygon], True, col, 2)
                        cx, cy = s.center
                        cv2.putText(overlay, str(s.slot_id), (cx - 10, cy - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2, cv2.LINE_AA)

                if back_mode:
                    pass
                elif confirmed:
                    fixed_pose = get_initial_car_pose()
                    draw_car_front(overlay, fixed_pose)
                else:
                    draw_car_front(overlay, car_pose)

                # 후진 모드에서 선택 슬롯 방향 곡선
                if back_mode and back_target_center is not None and (not in_third_video):
                    start_x = FRAME_W // 2
                    start_y = int(FRAME_H * 0.90)
                    end_x, end_y = back_target_center

                    full_curve = generate_back_curve(
                        start_x, start_y, end_x, end_y, num_points=60
                    )
                    if len(full_curve) >= 2:
                        curve_arr = np.array(full_curve, dtype=np.int32)
                        cv2.polylines(overlay, [curve_arr], False, (0, 255, 255), 3)

                # GO_FORWARD 단계의 빨간 점
                if confirmed and slam_goal is not None:
                    fixed_pose = get_initial_car_pose()
                    car_x, car_y = int(fixed_pose.x), int(fixed_pose.y)

                    # ★ 프리즈 상태에서는 진행도(progress)를 0으로 고정
                    if freeze and not back_mode:
                        progress = 0.0
                    else:
                        if back_mode:
                            progress = 1.0
                        elif path:
                            progress = follower.idx / float(len(path)) if len(path) > 0 else 0.0
                            progress = max(0.0, min(1.0, progress))
                        else:
                            progress = 0.0

                    goal_y0 = float(slam_goal["y"])
                    goal_x = car_x
                    dot_y = int(goal_y0 * (1.0 - progress) + car_y * progress)
                    dot_x = goal_x

                    cv2.line(overlay, (car_x, car_y), (dot_x, dot_y),
                            (255, 255, 255), 2)
                    cv2.circle(overlay, (dot_x, dot_y), 7, (0, 0, 255), -1)

                cv2.putText(overlay, mode_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                            (0, 255, 255), 2, cv2.LINE_AA)

                fps_text = f"FPS: {fps:4.1f}"
                cv2.putText(overlay, fps_text, (FRAME_W - 220, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                            (0, 255, 0), 2, cv2.LINE_AA)

                front_view_frame = overlay

                # ===== BEV 렌더링 =====
                try:
                    if back_mode and reverse_path and (not in_third_video):
                        bev_slots_to_draw = bev_static_slots if bev_static_slots else slots_to_draw
                        bev_path_to_draw  = bev_static_path  if bev_static_path  else path

                        idx = max(0, min(reverse_idx, len(reverse_path) - 1))
                        bev_car_pose_draw = reverse_path[idx]
                        bev_goal = None

                    elif confirmed and bev_static_path:
                        bev_slots_to_draw = bev_static_slots
                        bev_path_to_draw  = bev_static_path

                        if path and len(path) > 0:
                            progress = follower.idx / float(len(path))
                            progress = max(0.0, min(1.0, progress))
                        else:
                            progress = 0.0

                        if bev_forward_segment:
                            idx = int(progress * (len(bev_forward_segment) - 1))
                            idx = max(0, min(idx, len(bev_forward_segment) - 1))
                            bev_car_pose_draw = bev_forward_segment[idx]
                        else:
                            bev_car_pose_draw = bev_static_car_pose

                        bev_goal = None

                    else:
                        bev_slots_to_draw = slots_to_draw
                        bev_path_to_draw  = path
                        bev_car_pose_draw = car_pose
                        bev_goal = slam_goal

                    bev_frame = bev_renderer.render(
                        bev_slots_to_draw, bev_car_pose_draw, bev_path_to_draw, bev_goal
                    )
                except TypeError:
                    bev_frame = bev_renderer.render(slots_to_draw, car_pose, path)

        # 후진 모드에서 freeze가 풀린 이후에만 BEV 애니메이션 진행
        if back_mode and reverse_path and (not freeze):
            if reverse_idx < len(reverse_path) - 1:
                reverse_idx += 1

        time.sleep(0.02)



# =========================
# MJPEG 스트림 generator
# =========================
def mjpeg_generator(frame_name: str):
    global front_view_frame, bev_frame
    while True:
        with state_lock:
            frame = front_view_frame if frame_name == "front" else bev_frame
            if frame is not None:
                ok, buffer = cv2.imencode(".jpg", frame)
            else:
                ok, buffer = False, None

        if not ok or buffer is None:
            time.sleep(0.03)
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )
        time.sleep(0.03)


# =========================
# Flask 라우트
# =========================
@app.route("/front")
def stream_front():
    return Response(
        mjpeg_generator("front"),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/bev")
def stream_bev():
    return Response(
        mjpeg_generator("bev"),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/click", methods=["POST"])
def click():
    global pending_click
    data = request.get_json(force=True)
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    print("[HTTP CLICK]", x, y)
    with state_lock:
        pending_click = (x, y)
    return jsonify({"status": "ok", "x": x, "y": y})


@app.route("/start", methods=["POST"])
def start_video():
    global started, freeze
    with state_lock:
        # START 누르면 영상 재생 + 탐색 시작
        started = True
        freeze = False
    return jsonify({"status": "ok"})


@app.route("/reset", methods=["POST"])
def reset():
    global pending_reset
    with state_lock:
        pending_reset = True
    return jsonify({"status": "ok"})


FORWARD_PIXELS = 350
EARLY_RATIO = 0.9


@app.route("/confirm", methods=["POST"])
def confirm():
    global slam_goal, path, confirmed, freeze, car_pose
    global total_frames, video_frame_idx
    global bev_static_slots, bev_static_path, bev_static_car_pose, freeze_slots
    global bev_forward_segment

    with state_lock:
        if not path:
            return jsonify({"status": "no_path"}), 400

        bev_static_slots = freeze_slots.copy()
        bev_static_path  = list(path)
        bev_static_car_pose = car_pose

        bev_forward_segment = [p for p in bev_static_path if not p.reverse]
        if not bev_forward_segment:
            bev_forward_segment = list(bev_static_path)

        start = get_initial_car_pose()
        car_pose = start

        remaining_frames = max(total_frames - video_frame_idx, 1)
        steps = max(1, int(remaining_frames * EARLY_RATIO))

        print("[INFO] remaining_frames =", remaining_frames,
              "steps(early) =", steps,
              "total_frames =", total_frames,
              "video_frame_idx =", video_frame_idx)

        forward_y = max(start.y - FORWARD_PIXELS, 0)
        slam_goal = {
            "x": float(start.x),
            "y": float(forward_y),
        }
        print("[INFO] Parking goal (front-view ground) =", slam_goal)

        target = CarPose(slam_goal["x"], slam_goal["y"], start.yaw, reverse=False)
        forward_path = ParkingPlanner._straight_forward(
            start, target, steps=steps
        )

        path = forward_path
        follower.start(path)

        
        confirmed = True
        freeze = False

        return jsonify({"status": "ok", "goal": slam_goal})


@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Parking Demo (Detectron2)</title>
  <style>
    body { background:#222; color:#eee; font-family:sans-serif; }
    .row { display:flex; gap:10px; }
    img { border:1px solid #555; }
    button { margin-top:10px; padding:6px 12px; }
  </style>
</head>
<body>
  <h2>Parking Demo</h2>
  <div class="row">
    <div>
      <p>CameraView (여기를 클릭해서 슬롯 선택)</p>
      <img id="front" src="/front" width="1280" height="720" />
    </div>
    <div>
      <p>BEV</p>
      <img id="bev" src="/bev" width="600" height="600" />
    </div>
  </div>
  <button onclick="startVideo()">Start</button>
  <button onclick="resetParking()">Reset</button>
  <button onclick="confirmGoal()">Confirm</button>

  <script>
    const FRAME_W = 1280;
    const FRAME_H = 720;
    const frontImg = document.getElementById('front');

    frontImg.addEventListener('click', async (e) => {
      const rect = frontImg.getBoundingClientRect();
      const x = Math.round((e.clientX - rect.left) * (FRAME_W / rect.width));
      const y = Math.round((e.clientY - rect.top)  * (FRAME_H / rect.height));

      console.log("click:", x, y);

      try {
        const res = await fetch('/click', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({x, y})
        });
        const js = await res.json();
        console.log("server:", js);
      } catch (err) {
        console.error(err);
      }
    });

    async function startVideo() {
      try {
        const res = await fetch('/start', {method: 'POST'});
        const js = await res.json();
        console.log("start:", js);
      } catch (err) {
        console.error(err);
      }
    }

    async function resetParking() {
      try {
        const res = await fetch('/reset', {method: 'POST'});
        const js = await res.json();
        console.log("reset:", js);
      } catch (err) {
        console.error(err);
      }
    }

    async function confirmGoal() {
      try {
        const res = await fetch('/confirm', {method: 'POST'});
        const js = await res.json();
        console.log("confirm:", js);
        if (js.status === "ok") {
          alert("Parking area selected: (" + js.goal.x + ", " + js.goal.y + ")");
        } else {
          alert("No path to confirm.");
        }
      } catch (err) {
        console.error(err);
        alert("Failed to set Parking area");
      }
    }
  </script>
</body>
</html>
"""


# =========================
# 엔트리 포인트
# =========================
if __name__ == "__main__":
    t = threading.Thread(target=processing_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8001, debug=True, threaded=True)
