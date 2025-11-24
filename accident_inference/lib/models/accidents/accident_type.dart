enum AccidentType {
  collision,       // 추돌/전방 충돌
  contact,         // 약한 접촉
  sideswipe,       // 측면 스치기
  potholeImpact,   // 포트홀 충격
  objectImpact,    // 사물 충돌
  rollover,        // 전복
  unknown,         // 알 수 없음
}

extension AccidentTypeLabel on AccidentType {
  String get label {
    switch (this) {
      case AccidentType.collision:      return "전방 충돌";
      case AccidentType.contact:        return "약한 접촉";
      case AccidentType.sideswipe:      return "측면 스치기";
      case AccidentType.potholeImpact:  return "포트홀 충격";
      case AccidentType.objectImpact:   return "사물 충격";
      case AccidentType.rollover:       return "전복 사고";
      default:                          return "알 수 없음";
    }
  }
}