type Status = "pending" | "settled" | "rejected";
type Projection = { version: number; status: Status };

function parseProjection(input: unknown): Projection {
  if (typeof input !== "object" || input === null) {
    throw new Error("invalid object");
  }
  const x = input as Record<string, unknown>;
  if (typeof x.version !== "number" ||
      !Number.isSafeInteger(x.version) || x.version < 0) {
    throw new Error("invalid version");
  }
  if (typeof x.status !== "string" ||
      !["pending", "settled", "rejected"].includes(x.status)) {
    throw new Error("unsupported status");
  }
  return { version: x.version as number,
           status: x.status as Status };
}