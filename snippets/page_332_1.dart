enum PortState { requested, waitingDonor, authorized, active, cancelled }

String nextStep(PortState state) => switch (state) {
  PortState.requested => "Follow the verified confirmation instructions",
  PortState.waitingDonor => "Confirmation pending; track investigation",
  PortState.authorized => "Authorization received; activation pending",
  PortState.active => "Portability completed",
  PortState.cancelled => "This attempt was cancelled; review billing status",
};

// Billing status is a separate authorized projection.
// A customer tap does not produce donor authorization.