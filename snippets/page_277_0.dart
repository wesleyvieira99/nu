import 'package:flutter/material.dart';

class PendingPayment extends StatelessWidget {
  const PendingPayment({super.key, required this.onDetails});
  final VoidCallback onDetails;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Card(
      color: colors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.schedule, color: colors.onSurface),
            const SizedBox(height: 8),
            Text('Pagamento em processamento',
                style: TextStyle(color: colors.onSurface)),
            const SizedBox(height: 8),
            Text('Confira o andamento antes de tentar novamente.',
                style: TextStyle(color: colors.onSurface)),
            TextButton(onPressed: onDetails,
                child: const Text('Ver andamento')),
          ],
        ),
      ),
    );
  }
}