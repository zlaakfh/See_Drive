enum AccidentLevel {
  minor,      // 경미
  moderate,   // 보통
  severe,     // 심각
}

extension AccidentLevelLabel on AccidentLevel {
  String get label {
    switch (this) {
      case AccidentLevel.minor:
        return "경미한 충격";
      case AccidentLevel.moderate:
        return "중간 정도";
      case AccidentLevel.severe:
        return "심각한 사고";
    }
  }
}
