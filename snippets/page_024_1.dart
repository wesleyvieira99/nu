// Fragmento didático: imports e modelos do app são omitidos.
Widget statusPanel(JourneyState state) {
  final String label;
  switch (state) {
    case JourneyState.pending:
      label = 'Estamos confirmando a operação';
      break;
    case JourneyState.settled:
      label = 'Operação concluída';
      break;
    case JourneyState.rejected:
      label = 'Operação não concluída';
      break;
  }
  return Semantics(
    liveRegion: true,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Text(label),
    ),
  );
}