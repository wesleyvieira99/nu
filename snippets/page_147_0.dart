import 'package:flutter/material.dart';

class InvoiceSummary extends StatelessWidget {
  const InvoiceSummary({super.key, required this.total,
    required this.dueDate, required this.showChart,
    required this.chart});
  final String total;
  final String dueDate;
  final bool showChart;
  final Widget chart;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          header: true,
          child: Text('Total da fatura: $total'),
        ),
        Text('Vencimento: $dueDate'),
        if (showChart) chart,
      ],
    );
  }
}