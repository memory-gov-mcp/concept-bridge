import fixture from "../../../fixtures/bridge.sample.json";
import type { BridgeResult } from "../lib/api";

export const sample = fixture satisfies BridgeResult;
export const sampleQuery = sample.query;
