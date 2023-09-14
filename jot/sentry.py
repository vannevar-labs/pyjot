import sentry_sdk as sentry
from sentry_sdk.integrations.argv import ArgvIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

from jot import flush, log
from jot.base import Target


class SentryTarget(Target):
    "A target that sends telemetry to Sentry"

    @classmethod
    def init_sentry(cls, **kwargs):
        if sentry.Hub.current.client is not None:
            return

        integrations = [
            DedupeIntegration(),
            StdlibIntegration(),
            ModulesIntegration(),
            ArgvIntegration(),
            ThreadingIntegration(propagate_hub=True),
        ]
        sentry.init(default_integrations=False, integrations=integrations, **kwargs)
        flush.add_handler(cls.flush)

    @staticmethod
    def flush():
        client = sentry.Hub.current.client
        if client is not None:
            client.flush()

    def __init__(self, level=log.WARNING, **kwargs):
        self.init_sentry(**kwargs)
        super().__init__(level)
        self.spans = {}

    def start(self, trace_id=None, parent_id=None, id=None, name=None):
        span = super().start(trace_id, parent_id, id, name)

        if parent_id is not None and parent_id in self.spans:
            sentry_span = self.spans[parent_id].start_child(
                op=name,
                description=name,
                span_id=span.id_hex,
                same_process_as_parent=True,
            )
        else:
            sentry_span = sentry.start_transaction(
                op=name,
                name=name,
                trace_id=span.trace_id_hex,
                parent_span_id=span.parent_id_hex,
                span_id=span.id_hex,
                same_process_as_parent=False if parent_id is not None else None,
            )
        self.spans[span.id] = sentry_span

        return span

    def finish(self, tags, span):
        sentry_span = self.spans.pop(span.id, None)
        if sentry_span is not None:
            for k, v in tags.items():
                sentry_span.set_tag(k, v)
            sentry_span.finish()

    def log(self, level, message, tags, span=None):
        sentry.capture_message(
            message,
            level=log.name(level),
            contexts=_extract_contexts(span),
            tags=tags,
        )

    def error(self, message, exception, tags, span=None):
        sentry.capture_exception(
            exception,
            level="error",
            contexts=_extract_contexts(span),
            extras={"message": message},
            tags=tags,
        )


def _extract_contexts(span=None):
    if span is None:
        return None
    contexts = {"trace": {"trace_id": span.trace_id_hex, "span_id": span.id_hex, "op": span.name}}
    if span.parent_id is not None:
        contexts["trace"]["parent_span_id"] = span.parent_id_hex
    return contexts
