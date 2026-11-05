"""Route delegated tasks to specialized backstage workers."""

from typing import Any

from agent.delegation_provider import DelegationProvider


DEFAULT_WORKERS: dict[str, dict[str, str]] = {
    "scout": {
        "model": "deepseek/deepseek-v4-flash",
        "provider": "nous",
        "reasoning_effort": "low",
        "service_tier": "fast",
        "desc": "Fast reader for raw files, logs, and URLs",
    },
    "librarian": {
        "model": "qwen/qwen3.7-flash",
        "provider": "nous",
        "reasoning_effort": "low",
        "service_tier": "fast",
        "desc": "Multi-source searcher returning cited excerpts only",
    },
    "code_monkey": {
        "model": "deepseek/deepseek-v4.1-flash",
        "provider": "nous",
        "reasoning_effort": "low",
        "service_tier": "fast",
        "desc": "Execution mechanic for tests, compilation, repo greps",
    },
    "adversary": {
        "model": "anthropic/claude-haiku-5.5",
        "provider": "nous",
        "reasoning_effort": "medium",
        "service_tier": "fast",
        "desc": "Red-team auditor finding holes and risks in proposals",
    },
    "briefer": {
        "model": "deepseek/deepseek-v4-flash",
        "provider": "nous",
        "reasoning_effort": "low",
        "service_tier": "fast",
        "desc": "Executive summarizer pre-digesting heavy dumps into briefs",
    },
}


class StagehandsProvider(DelegationProvider):
    """Delegate by worker role while retaining the sovereign as fallback."""

    @property
    def name(self) -> str:
        return "stagehands"

    @property
    def summary(self) -> str:
        return "Route delegated tasks to specialized backstage workers."

    def _workers(self, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return self.settings(config).get("workers") or DEFAULT_WORKERS

    def description(self, config: dict[str, Any]) -> str:
        workers = "; ".join(
            f"{name}: {worker.get('desc', name)}"
            for name, worker in self._workers(config).items()
        )
        return (
            f"Available backstage workers: {workers}. "
            "Omitted or unknown workers use the parent sovereign model and provider."
        )

    def is_available(self) -> bool:
        return True

    def task_parameters(self, config: dict[str, Any]) -> dict[str, Any]:
        workers = list(self._workers(config))
        return {
            "worker": {
                "type": "string",
                "enum": workers,
                "description": "Backstage worker role for this task: "
                + ", ".join(workers),
            }
        }

    def route_task(
        self, task: dict[str, Any], config: dict[str, Any]
    ) -> dict[str, Any]:
        worker_name = task.get("worker")
        workers = self._workers(config)
        worker = workers.get(worker_name) if isinstance(worker_name, str) else None
        if worker is not None:
            return {
                "provider": worker.get("provider"),
                "model": worker.get("model"),
                "reasoning_effort": worker.get("reasoning_effort"),
                "service_tier": worker.get("service_tier"),
                "label": worker_name,
            }

        model = config.get("model")
        provider = config.get("provider")
        if isinstance(model, dict):
            provider = model.get("provider", provider)
            model = model.get("default")
        return {
            "provider": provider,
            "model": model,
            "reasoning_effort": config.get("reasoning_effort"),
            "service_tier": config.get("service_tier"),
            "label": "sovereign",
        }
