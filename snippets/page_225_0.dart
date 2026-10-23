enum JourneyOutcome { completed, failed, unknown }

class JourneySignal {
  final String attemptId;
  final String release;
  final JourneyOutcome outcome;
  final int elapsedMs;
  const JourneySignal(this.attemptId, this.release,
      this.outcome, this.elapsedMs);
}

abstract class BoundedTelemetry {
  bool offer(JourneySignal signal);
}

Future<T> observed<T>(
  Future<T> Function() task,
  BoundedTelemetry telemetry,
  String attemptId,
  String release,
) async {
  final watch = Stopwatch()..start();
  try {
    final result = await task();
    telemetry.offer(JourneySignal(attemptId, release,
        JourneyOutcome.completed, watch.elapsedMilliseconds));
    return result;
  } catch (_) {
    telemetry.offer(JourneySignal(attemptId, release,
        JourneyOutcome.unknown, watch.elapsedMilliseconds));
    rethrow;
  }
}