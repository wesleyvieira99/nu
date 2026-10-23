class CivilDate implements Comparable<CivilDate> {
  final int year, month, day;
  const CivilDate(this.year, this.month, this.day);
  int get orderKey => year * 10000 + month * 100 + day;
  @override
  int compareTo(CivilDate other) =>
      orderKey.compareTo(other.orderKey);
}

class BillView {
  final String id;
  final CivilDate due;
  final int cents;
  final bool paid;
  const BillView(this.id, this.due, this.cents, this.paid);
}

List<BillView> upcoming(List<BillView> source) {
  // Datas já validadas na fronteira do contrato proposto.
  final visible = source.where((bill) => !bill.paid).toList();
  visible.sort((a, b) {
    final byDate = a.due.compareTo(b.due);
    return byDate != 0 ? byDate : a.id.compareTo(b.id);
  });
  return List.unmodifiable(visible);
}