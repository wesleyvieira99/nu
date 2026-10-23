import 'package:flutter/material.dart';

class AssistedRecovery extends StatelessWidget {
  const AssistedRecovery({super.key, required this.onHelp});
  final VoidCallback onHelp;

  @override
  Widget build(BuildContext context) {
    return FocusTraversalGroup(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: const Text('Continue a ativação com ajuda'),
          ),
          const SizedBox(height: 12),
          Semantics(
            liveRegion: true,
            child: const Text(
              'A câmera está indisponível. Seu cartão ainda não '
              'foi ativado. Há outra forma de continuar.',
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: onHelp,
            child: const Text('Obter ajuda para continuar'),
          ),
        ],
      ),
    );
  }
}