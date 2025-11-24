// example/lib/models/accidents/accident_rule.dart
import 'dart:math' as math;

import '../hazard/hazard_class.dart';
import '../hazard/hazard_detection.dart';
import 'accident_type.dart';
import 'accident_level.dart';
import 'accident_decision.dart';
import 'package:flutter/foundation.dart'; // ✅ debugPrint 사용하려면 필요

class ImuSnapshot {
  final int tUs;
  final double ax, ay, az;
  final double gx, gy, gz;
  final double lax, lay, laz;

  const ImuSnapshot({
    required this.tUs,
    required this.ax, required this.ay, required this.az,
    required this.gx, required this.gy, required this.gz,
    required this.lax, required this.lay, required this.laz,
  });

  double get accMag => math.sqrt(ax*ax + ay*ay + az*az);
  double get linAccMag => math.sqrt(lax*lax + lay*lay + laz*laz);
  double get gyroMag => math.sqrt(gx*gx + gy*gy + gz*gz);

  double get tiltDeg {
    final g = accMag;
    if (g < 1e-6) return 0.0;
    final cosTheta = (az / g).clamp(-1.0, 1.0);
    return math.acos(cosTheta) * 180.0 / math.pi;
  }
}

class AccidentRuleEngine {
  static ImuSnapshot? _prev;

  // ✅ 증거 누적 카운터
  static int _minorStreak = 0;
  static int _moderateStreak = 0;
  static int _severeStreak = 0;

  // ✅ 연속 N프레임 이상일 때만 확정
  static const int needMinorFrames = 3;
  static const int needModerateFrames = 2;
  static const int needSevereFrames = 1; // severe는 1번만 튀어도 OK

  // ✅ 팝업 쿨다운(연속 알림 방지)
  static int _lastDecisionUs = 0;
  static const int cooldownUs = 3000000; // 3초

  // 임계값: 조금 둔감하게 상향
  static const double a1 = 2.5;
  static const double a2 = 6.0;
  static const double a3 = 10.0;

  static const double g1 = 0.8;
  static const double g2 = 1.5;
  static const double g3 = 2.2;

  // static const double a1 = 0.5;
  // static const double a2 = 1.2;
  // static const double a3 = 2.0;

  // static const double g1 = 0.2;
  // static const double g2 = 0.5;
  // static const double g3 = 0.9;


  static const double tiltSevereDeg = 80.0;
  static const int hazardWindowUs = 800000;

  static AccidentDecision? decide({
    required List<HazardDetection> hazards,
    required ImuSnapshot imu,
  }) {
    print("🟡 decide called t=${imu.tUs}");
    // --- cooldown ---
    if (_lastDecisionUs != 0 &&
        (imu.tUs - _lastDecisionUs).abs() < cooldownUs) {
      print("⏸️ cooldown skip");
      _prev = imu;
      return null;
    }

    final prev = _prev;
    _prev = imu;
    if (prev == null) {
      print("🟠 prev null (first frame)");
      return null;
  }

    // Δ
    final dLinAcc = (imu.linAccMag - prev.linAccMag).abs();
    final dGyro   = (imu.gyroMag   - prev.gyroMag).abs();
    final dLax = (imu.lax - prev.lax).abs();
    final dLay = (imu.lay - prev.lay).abs();
    final dLaz = (imu.laz - prev.laz).abs();
    print("📌 Δcalc lin=${dLinAcc.toStringAsFixed(4)}, "
      "gyro=${dGyro.toStringAsFixed(4)}, "
      "lax=${dLax.toStringAsFixed(4)}, lay=${dLay.toStringAsFixed(4)}, laz=${dLaz.toStringAsFixed(4)}, "
      "tilt=${imu.tiltDeg.toStringAsFixed(2)}");



    
    // recent hazards
    final recentHazards = hazards.where((h) {
      final dt = (imu.tUs - h.tUs).abs();
      return dt <= hazardWindowUs;
    }).toList();

    bool hasHazard(Set<HazardClass> set) =>
        recentHazards.any((h) => set.contains(h.hazard));

    final hasPothole = hasHazard({HazardClass.pothole});
    final hasVehicle = hasHazard({HazardClass.car, HazardClass.truck, HazardClass.bus});
    final hasSoftObj = hasHazard({HazardClass.animal, HazardClass.person});
    final hasHardObj = hasHazard({
      HazardClass.stone, HazardClass.box, HazardClass.garbageBag, HazardClass.constructionSign,
    });

    final hasAnyHazard = recentHazards.isNotEmpty;

    // ----- level 후보 계산 -----
    AccidentLevel? levelCandidate;
    if (dLinAcc > a3 || dGyro > g3 || imu.tiltDeg > tiltSevereDeg) {
      levelCandidate = AccidentLevel.severe;
    } else if (dLinAcc > a2 || dGyro > g2) {
      levelCandidate = AccidentLevel.moderate;
    } else if (dLinAcc > a1 || dGyro > g1) {
      levelCandidate = AccidentLevel.minor;
    } else {
      // streak 초기화
      _minorStreak = _moderateStreak = _severeStreak = 0;
      return null;
    }

    // ✅ Hazard 없으면 minor/moderate는 누적만 하고 확정 X
    if (!hasAnyHazard && levelCandidate != AccidentLevel.severe) {
      _minorStreak = _moderateStreak = 0;
      return null;
    }

    // ----- streak 누적 -----
    if (levelCandidate == AccidentLevel.minor) {
      _minorStreak++;
      _moderateStreak = _severeStreak = 0;
      if (_minorStreak < needMinorFrames) return null;
    } else if (levelCandidate == AccidentLevel.moderate) {
      _moderateStreak++;
      _minorStreak = _severeStreak = 0;
      if (_moderateStreak < needModerateFrames) return null;
    } else {
      _severeStreak++;
      _minorStreak = _moderateStreak = 0;
      if (_severeStreak < needSevereFrames) return null;
    }

    final level = levelCandidate;

    // ----- type 결정 -----
    AccidentType type;
    String reason;

    if (level == AccidentLevel.severe &&
        (imu.tiltDeg > tiltSevereDeg || dGyro > g3)) {
      type = AccidentType.rollover;
      reason = "전복/대충격(기울기 ${imu.tiltDeg.toStringAsFixed(1)}°, gyroΔ ${dGyro.toStringAsFixed(2)})";
    } else if (hasVehicle && dLinAcc > a2 && (dLax > dLaz || dLay > dLaz)) {
      type = AccidentType.collision;
      reason = "차량 탐지 + 강한 XY 충격";
    } else if (hasVehicle && dLay > a1 && dLay > dLax) {
      type = AccidentType.sideswipe;
      reason = "차량 탐지 + 측면(Y) 충격";
    } else if (hasPothole && dLaz > a1) {
      type = AccidentType.potholeImpact;
      reason = "포트홀 탐지 + Z 충격";
    } else if ((hasHardObj || hasSoftObj) && dLinAcc > a1) {
      type = AccidentType.objectImpact;
      reason = "사물 탐지 + 충격";
    } else if (level != AccidentLevel.severe) {
      // ✅ hazard 있는데 약한 충격이면 contact
      type = AccidentType.contact;
      reason = "약한 충격 + 위험요소 동반";
    } else {
      type = AccidentType.collision;
      reason = "강충격(severe) 단독 감지";
    }

    final decision = AccidentDecision(
      tUs: imu.tUs,
      type: type,
      level: level,
      reason: reason,
      hazards: recentHazards,
      linAccMag: dLinAcc,
      gyroMag: dGyro,
    );

    _lastDecisionUs = imu.tUs;
    _minorStreak = _moderateStreak = _severeStreak = 0;
    return decision;
  }
}
