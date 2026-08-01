"""Dynamic prompt loading, rendering, versioning, and localization support."""

from dataclasses import dataclass
from importlib import import_module
from string import Formatter


class PromptNotFoundError(LookupError):
    """Raised when an agent, version, locale, or template is not registered."""


class PromptVariableError(ValueError):
    """Raised when a prompt template is rendered without all required variables."""


@dataclass(frozen=True)
class ResolvedPrompt:
    """A rendered prompt plus its stable version and locale metadata."""

    content: str
    agent: str
    template: str
    version: str
    locale: str


class PromptManager:
    """Load prompt modules dynamically without embedding templates inside agents."""

    def __init__(self, *, default_version: str = "v1", default_locale: str = "en") -> None:
        self._default_version = default_version
        self._default_locale = default_locale

    def render(
        self,
        agent: str,
        template: str = "task",
        *,
        version: str | None = None,
        locale: str | None = None,
        variables: dict[str, object] | None = None,
    ) -> ResolvedPrompt:
        """Render one template using explicit version/locale selection and strict variables."""
        selected_version = version or self._default_version
        selected_locale = self._resolve_locale(agent, selected_version, locale or self._default_locale)
        templates = self._templates(agent, selected_version, selected_locale)
        try:
            source = templates[template]
        except KeyError as error:
            raise PromptNotFoundError(
                f"Prompt template '{template}' is not registered for agent '{agent}'."
            ) from error
        return ResolvedPrompt(
            content=self._format(source, variables or {}),
            agent=agent,
            template=template,
            version=selected_version,
            locale=selected_locale,
        )

    def render_agent_prompt(
        self,
        agent: str,
        *,
        version: str | None = None,
        locale: str | None = None,
        variables: dict[str, object] | None = None,
    ) -> ResolvedPrompt:
        """Compose the global system template and an agent task template for future use."""
        selected_version = version or self._default_version
        selected_locale = locale or self._default_locale
        system_prompt = self.render(
            "system",
            "system",
            version=selected_version,
            locale=selected_locale,
            variables=variables,
        )
        agent_prompt = self.render(
            agent,
            "task",
            version=selected_version,
            locale=selected_locale,
            variables=variables,
        )
        return ResolvedPrompt(
            content=f"{system_prompt.content}\n\n{agent_prompt.content}",
            agent=agent,
            template="composed",
            version=agent_prompt.version,
            locale=agent_prompt.locale,
        )

    def available_versions(self, agent: str) -> list[str]:
        """Return registered versions for an agent, enabling controlled prompt rollout."""
        return sorted(self._module_prompts(agent))

    def _resolve_locale(self, agent: str, version: str, requested_locale: str) -> str:
        prompts = self._module_prompts(agent)
        if version not in prompts:
            raise PromptNotFoundError(f"Prompt version '{version}' is not registered for agent '{agent}'.")
        locales = prompts[version]
        candidates = [requested_locale, requested_locale.split("-", maxsplit=1)[0], self._default_locale]
        for candidate in candidates:
            if candidate in locales:
                return candidate
        raise PromptNotFoundError(f"No locale is registered for agent '{agent}' version '{version}'.")

    def _templates(self, agent: str, version: str, locale: str) -> dict[str, str]:
        return self._module_prompts(agent)[version][locale]

    @staticmethod
    def _format(template: str, variables: dict[str, object]) -> str:
        required_variables = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None and not field_name.isdigit()
        }
        missing = required_variables.difference(variables)
        if missing:
            raise PromptVariableError(f"Missing prompt variables: {', '.join(sorted(missing))}.")
        try:
            return template.format(**variables)
        except (KeyError, IndexError, ValueError) as error:
            raise PromptVariableError("Prompt variables could not be rendered.") from error

    @staticmethod
    def _module_prompts(agent: str) -> dict[str, dict[str, dict[str, str]]]:
        if not agent.replace("_", "").isalpha():
            raise PromptNotFoundError("Prompt agent names must contain only letters and underscores.")
        try:
            module = import_module(f"app.prompts.{agent}")
            return module.PROMPTS
        except (ImportError, AttributeError) as error:
            raise PromptNotFoundError(f"Prompt module for agent '{agent}' is not registered.") from error
