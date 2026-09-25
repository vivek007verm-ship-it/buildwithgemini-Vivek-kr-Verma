import json
import re

try:
    from a2ui.basic_catalog.provider import BasicCatalog
    from a2ui.schema.manager import A2uiSchemaManager
    HAS_A2UI = True
except ImportError:
    HAS_A2UI = False

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types


def get_a2ui_system_prompt(role_description: str) -> str:
    """Builds the system prompt with A2uiSchemaManager (version 0.8) and the Basic Catalog.

    Args:
        role_description: The base role instruction for the agent.

    Returns:
        The combined system instruction text containing A2UI UI guidelines and schema specs.
    """
    if HAS_A2UI:
        try:
            catalog_config = BasicCatalog().get_config("0.8")
            schema_manager = A2uiSchemaManager(version="0.8", catalogs=[catalog_config])
            return schema_manager.generate_system_prompt(role_description)
        except Exception:
            pass
    return role_description


def a2ui_after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """ADK after_model_callback that processes <a2ui-json> blocks into application/a2ui+json parts.

    Args:
        callback_context: ADK CallbackContext for the invocation turn.
        llm_response: LlmResponse output from the model.

    Returns:
        Updated LlmResponse with A2UI parts converted to application/a2ui+json MIME type blobs.
    """
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        return None

    new_parts = []
    has_a2ui = False

    for part in llm_response.content.parts:
        if part.text and "<a2ui-json>" in part.text:
            has_a2ui = True
            pattern = r"<a2ui-json>(.*?)</a2ui-json>"
            pos = 0
            for match in re.finditer(pattern, part.text, re.DOTALL):
                prefix = part.text[pos : match.start()].strip()
                if prefix:
                    new_parts.append(types.Part.from_text(text=prefix))

                json_str = match.group(1).strip()
                try:
                    data = json.loads(json_str)
                    data_bytes = json.dumps(data).encode("utf-8")
                    new_parts.append(
                        types.Part.from_bytes(
                            data=data_bytes,
                            mime_type="application/a2ui+json",
                        )
                    )
                except Exception:
                    new_parts.append(
                        types.Part.from_text(text=f"<a2ui-json>{json_str}</a2ui-json>")
                    )

                pos = match.end()

            suffix = part.text[pos:].strip()
            if suffix:
                new_parts.append(types.Part.from_text(text=suffix))
        else:
            new_parts.append(part)

    if has_a2ui:
        llm_response.content.parts = new_parts

    return llm_response
