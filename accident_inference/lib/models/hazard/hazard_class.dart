/// Hazard object detected by YOLO.
/// Matches YOLO detection classes.
enum HazardClass {
  animal,          // 동물
  person,          // 사람
  garbageBag,      // 쓰레기 봉투/자루
  constructionSign, // 공사 표지판, 불법 주정차 금지판
  box,             // 박스
  stone,           // 도로 위 돌멩이
  pothole,         // 포트홀
  car,             // 승용차
  truck,           // 트럭
  bus;             // 버스
}

extension HazardClassName on HazardClass {
  String get label {
    switch (this) {
      case HazardClass.animal:
        return "Animal";
      case HazardClass.person:
        return "Person";
      case HazardClass.garbageBag:
        return "Garbage Bag";
      case HazardClass.constructionSign:
        return "Construction Sign";
      case HazardClass.box:
        return "Box";
      case HazardClass.stone:
        return "Stone";
      case HazardClass.pothole:
        return "Pothole";
      case HazardClass.car:
        return "Car";
      case HazardClass.truck:
        return "Truck";
      case HazardClass.bus:
        return "Bus";
    }
  }
}
