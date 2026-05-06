import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useState } from "react";

import { SSEEvent, useQueryStream } from "../../lib/sse";

interface Step {
  agent: string;
  status: "pending" | "running" | "complete" | "failed";
  duration_ms?: number;
  detail?: string;
}

const KNOWN_AGENTS = [
  "IntentClassifier",
  "Retrieval",
  "Synthesis",
  "Drafting",
  "ClaimParser",
  "EntailmentChecker",
  "WebResearch",
  "ResolutionGate"
];

interface Props {
  queryId: string;
  onComplete: () => void;
  onFailed: (error: string) => void;
}

export function AgentProgressFeed({ queryId, onComplete, onFailed }: Props) {
  const [steps, setSteps] = useState<Step[]>(
    KNOWN_AGENTS.map((agent) => ({ agent, status: "pending" }))
  );
  const [done, setDone] = useState(false);

  const handleEvent = useCallback(
    (event: SSEEvent) => {
      setSteps((previous) => {
        const next = [...previous];
        if (event.event === "agent_start" && event.agent) {
          const index = next.findIndex((step) => step.agent === event.agent);
          if (index >= 0) next[index] = { ...next[index], status: "running" };
        }
        if (event.event === "agent_complete" && event.agent) {
          const index = next.findIndex((step) => step.agent === event.agent);
          if (index >= 0) {
            next[index] = {
              ...next[index],
              status: "complete",
              duration_ms: event.duration_ms,
              detail:
                typeof event.chunks_found === "number"
                  ? `${event.chunks_found} chunks`
                  : undefined
            };
          }
        }
        if (event.event === "agent_skipped" && event.agent) {
          const index = next.findIndex((step) => step.agent === event.agent);
          if (index >= 0) next[index] = { ...next[index], detail: "skipped" };
        }
        if (event.event === "pipeline_failed" && event.agent) {
          const index = next.findIndex((step) => step.agent === event.agent);
          if (index >= 0) next[index] = { ...next[index], status: "failed" };
        }
        return next;
      });

      if (event.event === "pipeline_failed") {
        setDone(true);
        onFailed((event.error as string) ?? "Pipeline failed");
      }
      if (event.event === "pipeline_complete") {
        setDone(true);
        onComplete();
      }
    },
    [onComplete, onFailed]
  );

  useQueryStream(queryId, handleEvent, !done);

  const icon = (status: Step["status"]) =>
    status === "complete" ? "o" : status === "running" ? "..." : status === "failed" ? "x" : ".";
  const color = (status: Step["status"]) =>
    ({
      complete: "text-verified",
      running: "text-accent animate-pulse",
      failed: "text-purged",
      pending: "text-gray-600"
    }[status]);

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-5 font-mono text-sm space-y-2">
      <p className="text-gray-400 text-xs mb-3 uppercase tracking-widest">Pipeline Execution</p>
      <AnimatePresence>
        {steps.map((step) => (
          <motion.div
            key={step.agent}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center justify-between"
          >
            <span className={`${color(step.status)} w-5`}>{icon(step.status)}</span>
            <span className="flex-1 ml-2 text-gray-300">{step.agent}</span>
            {step.duration_ms && <span className="text-gray-500 text-xs">{step.duration_ms}ms</span>}
            {step.detail && <span className="text-gray-500 text-xs ml-3">{step.detail}</span>}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
