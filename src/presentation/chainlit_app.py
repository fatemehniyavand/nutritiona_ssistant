import os
import sys
import re
import json
import traceback
from datetime import datetime
from types import SimpleNamespace

import chainlit as cl

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

IMPORT_ERROR = None
IMPORT_TRACEBACK = None

try:
    from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
    from src.domain.models.conversation_memory import MemoryEntry
    from src.domain.models.meal_state import MealState
except Exception as e:
    NutritionOrchestrator = None
    MemoryEntry = None
    MealState = None
    IMPORT_ERROR = str(e)
    IMPORT_TRACEBACK = traceback.format_exc()

orchestrator = None

EMPTY_MESSAGE = "Your message is empty."
NON_ENGLISH_MESSAGE = "Please use English for food and nutrition queries."
QUANTITY_ONLY_MESSAGE = "I can see the quantity, but the food name is missing."
FOOD_NOT_CONFIDENT_MESSAGE = "This looks like a food name, but I could not confidently match it."
NON_DIGIT_QUANTITY_MESSAGE = "I recognized a quantity expression, but it is not written with digits."
UNCLEAR_MESSAGE = "I could not confidently understand your input."

CLEAR_MEAL_COMMANDS = {
    "clear meal",
    "reset meal",
    "empty meal",
    "clear the meal",
    "delete meal",
    "start over",
}

REMOVE_PREFIXES = ("remove ", "delete ", "take out ")


def get_meal_state():
    if MealState is None:
        return None
    return cl.user_session.get("meal_state") or MealState()


def badge_confidence(confidence: str) -> str:
    value = (confidence or "").lower()

    if value == "high":
        return "🟢 High"
    if value == "medium":
        return "🟡 Medium"
    if value == "low":
        return "🔴 Low"

    return f"⚪ {confidence or 'Unknown'}"


def badge_status(status: str) -> str:
    value = (status or "").lower()

    if value in {"matched", "ok", "success"}:
        return f"✅ {status}"
    if value in {"unclear", "partial"}:
        return f"🟡 {status}"
    if value in {"not_found", "rejected", "error"}:
        return f"❌ {status}"

    return f"• {status or 'Unknown'}"


def format_suggestions_inline(suggestions) -> str:
    if not suggestions:
        return ""
    return " | ".join([f"`{item}`" for item in suggestions])


def get_last_debug_payload() -> str:
    return cl.user_session.get("last_debug_payload") or ""


def set_last_debug_payload(value: str) -> None:
    cl.user_session.set("last_debug_payload", value or "")


def is_debug_enabled() -> bool:
    return bool(cl.user_session.get("debug_enabled", False))


def set_debug_enabled(enabled: bool) -> None:
    cl.user_session.set("debug_enabled", bool(enabled))


def get_debug_actions():
    label = "Debug: ON" if is_debug_enabled() else "Debug: OFF"
    return [
        cl.Action(name="toggle_debug", label=label, payload={}),
        cl.Action(name="show_debug", label="Show Debug", payload={}),
    ]


def build_debug_element(debug_payload: str) -> cl.Text:
    return cl.Text(
        name="debug_response.json",
        content=debug_payload,
        display="side",
    )


def format_number(value) -> str:
    if value is None:
        return "Unknown"
    try:
        number = float(value)
        return str(int(number)) if number.is_integer() else str(round(number, 2))
    except Exception:
        return str(value)


def normalize_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*(grams|gram|g)\b", r"\1g", text)
    text = re.sub(r"(\d+(?:\.\d+)?g)(and|add|with|plus)\b", r"\1 \2", text)
    text = re.sub(r"\b(and|add|with|plus)([a-z])", r"\1 \2", text)
    text = re.sub(r"[,\;\|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_command(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_clear_meal_query(text: str) -> bool:
    return normalize_command(text) in CLEAR_MEAL_COMMANDS


def get_remove_target(text: str) -> str:
    normalized = normalize_command(text)
    for prefix in REMOVE_PREFIXES:
        if normalized.startswith(prefix):
            return normalized[len(prefix):].strip()
    return ""


def build_item_block(item, idx: int) -> str:
    lines = []

    title = getattr(item, "matched_food", None) or getattr(item, "input_food", f"Item {idx}")
    lines.append(f"## {idx}. {title}")
    lines.append("")
    lines.append(f"**Input:** `{getattr(item, 'input_food', 'Unknown')}`  ")
    lines.append(f"**Status:** {badge_status(getattr(item, 'status', 'Unknown'))}  ")
    lines.append(f"**Confidence:** {badge_confidence(getattr(item, 'confidence', 'Unknown'))}")

    details = []

    if getattr(item, "grams", None) is not None:
        details.append(f"- **Grams:** `{format_number(item.grams)} g`")

    if getattr(item, "matched_food", None):
        details.append(f"- **Matched food:** `{item.matched_food}`")

    if getattr(item, "kcal_per_100g", None) is not None:
        details.append(f"- **kcal per 100g:** `{format_number(item.kcal_per_100g)}`")

    if getattr(item, "calories", None) is not None:
        details.append(f"- **Estimated calories:** `{format_number(item.calories)} kcal`")

    if getattr(item, "match_reason", None):
        details.append(f"- **Match reason:** {item.match_reason}")

    if getattr(item, "match_source", None):
        details.append(f"- **Match source:** `{item.match_source}`")

    if getattr(item, "why_rejected", None):
        details.append(f"- **Why rejected:** {item.why_rejected}")

    if getattr(item, "suggestions", None):
        details.append(f"- **Suggestions:** {format_suggestions_inline(item.suggestions)}")

    if details:
        lines.append("")
        lines.extend(details)

    return "\n".join(lines)


def build_current_meal_block(meal_state) -> str:
    if meal_state is None:
        return ""

    items = getattr(meal_state, "items", []) or []
    if not items:
        return (
            "### Current Meal Memory\n\n"
            "- *(empty)*\n"
        )

    lines = ["### Current Meal Memory", ""]
    for item in items:
        lines.append(
            f"- `{item.food}` — `{format_number(item.grams)} g` → `{format_number(item.calories)} kcal`"
        )

    lines.append("")
    lines.append(f"**Meal total:** `{format_number(getattr(meal_state, 'total_calories', 0))} kcal`")
    return "\n".join(lines)


def format_calorie_response(response, meal_state=None) -> str:
    lines = []

    lines.append("# 🍽️ Nutrition Assistant")
    lines.append("")
    lines.append("## Calorie Estimation")
    lines.append("")
    lines.append("### Summary")
    lines.append(f"- **Request calories:** `{format_number(getattr(response, 'total_calories', 0))} kcal`")
    lines.append(f"- **Coverage:** `{getattr(response, 'coverage', '0/0')}`")
    lines.append(
        f"- **Matched items:** `{getattr(response, 'matched_items', 0)}/{getattr(response, 'total_items', 0)}`"
    )
    lines.append(f"- **Overall confidence:** {badge_confidence(getattr(response, 'confidence', 'Unknown'))}")
    lines.append("")

    items = getattr(response, "items", None) or []
    if items:
        lines.append("### Item Breakdown")
        lines.append("")
        for idx, item in enumerate(items, start=1):
            lines.append(build_item_block(item, idx))
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.append("### Final Message")
    lines.append(getattr(response, "final_message", ""))

    suggestions = getattr(response, "suggestions", None) or []
    if suggestions:
        lines.append("")
        lines.append("### Global Suggestions")
        for suggestion in suggestions:
            lines.append(f"- `{suggestion}`")

    meal_block = build_current_meal_block(meal_state)
    if meal_block:
        lines.append("")
        lines.append(meal_block)

    return "\n".join(lines)


def format_guard_or_simple_qa_response(response) -> str:
    answer = (getattr(response, "answer", "") or "").strip()
    final_message = (getattr(response, "final_message", "") or "").strip()

    if answer == NON_ENGLISH_MESSAGE:
        return (
            "# ⚠️ Please use English\n\n"
            "This assistant supports **English food and nutrition queries** for reliable parsing.\n\n"
            "### Try these examples\n"
            "- `apple 200g`\n"
            "- `rice 150g`\n"
            "- `Is avocado healthy?`\n\n"
            "**Meal memory:** not changed."
        )

    if answer == EMPTY_MESSAGE:
        return (
            "# ⚠️ Your message is empty\n\n"
            "Please type a food query or a nutrition question in English.\n\n"
            "### Examples\n"
            "- `apple 200g`\n"
            "- `brown rice 150g and milk 200g`\n"
            "- `What are good sources of protein?`\n\n"
            "**Meal memory:** not changed."
        )

    if answer == QUANTITY_ONLY_MESSAGE:
        return (
            "# ⚠️ Food name missing\n\n"
            "I can see the quantity, but I still need the **food name**.\n\n"
            "### Examples\n"
            "- `apple 200g`\n"
            "- `rice 150g`\n\n"
            "**Meal memory:** not changed."
        )

    if answer.startswith("I recognized '") and "but I still need the quantity in grams." in answer:
        food_name = (
            answer
            .replace("I recognized '", "")
            .replace("', but I still need the quantity in grams.", "")
        )
        return (
            "# ⚠️ Quantity missing\n\n"
            f"I recognized **{food_name}**, but I still need the amount in grams.\n\n"
            "### Example\n"
            f"- `{food_name} 200g`\n\n"
            "**Meal memory:** not changed."
        )

    if answer == FOOD_NOT_CONFIDENT_MESSAGE:
        return (
            "# ⚠️ Food not recognized confidently\n\n"
            "This looks like a food name, but I could not confidently match it in the current calorie database.\n\n"
            "### Try these examples\n"
            "- `apple 200g`\n"
            "- `banana 100g`\n"
            "- `brown rice 150g`\n\n"
            "**Meal memory:** not changed."
        )

    if answer == NON_DIGIT_QUANTITY_MESSAGE:
        return (
            "# ⚠️ Quantity must use digits\n\n"
            "I recognized the quantity expression, but it must be written with digits for calorie estimation.\n\n"
            "### Correct examples\n"
            "- `apple 200g`\n"
            "- `banana 100g`\n"
            "- `rice 150g`\n\n"
            "> Write `200g`, not `two hundred grams`.\n\n"
            "**Meal memory:** not changed."
        )

    if answer == UNCLEAR_MESSAGE:
        return (
            "# ⚠️ Input unclear\n\n"
            "I could not confidently understand your input.\n\n"
            "### Try one of these\n"
            "- `banana 120g`\n"
            "- `chicken 200g and rice 100g`\n"
            "- `Is rice good for weight loss?`\n\n"
            "**Meal memory:** not changed."
        )

    lines = [
        "# 🥗 Nutrition Assistant",
        "",
        answer,
        "",
        f"**Confidence:** {badge_confidence(getattr(response, 'confidence', 'Unknown'))}",
    ]

    if final_message:
        lines.extend(["", final_message])

    lines.extend(["", "**Meal memory:** not changed."])
    return "\n".join(lines)


def format_qa_response(response) -> str:
    sources_used = getattr(response, "sources_used", []) or []
    retrieved_contexts = getattr(response, "retrieved_contexts", []) or []

    if not sources_used and not retrieved_contexts:
        return format_guard_or_simple_qa_response(response)

    lines = []

    lines.append("# 🥗 Nutrition Assistant")
    lines.append("")
    lines.append("## 📌 Answer")
    lines.append("")
    lines.append(getattr(response, "answer", ""))
    lines.append("")

    conf = (getattr(response, "confidence", "") or "").lower()
    if conf == "high":
        badge = "🟢 HIGH"
    elif conf == "medium":
        badge = "🟡 MEDIUM"
    else:
        badge = "🔴 LOW"

    lines.append(f"**Confidence:** {badge}")

    if sources_used:
        lines.append("")
        lines.append("## 📚 Sources Used")
        lines.append("")
        for i, source in enumerate(sources_used, 1):
            lines.append(f"{i}. `{source}`")

    if retrieved_contexts:
        lines.append("")
        lines.append("## 🧠 Retrieved Contexts")
        lines.append("")
        for idx, ctx in enumerate(retrieved_contexts, start=1):
            preview = ctx if len(ctx) <= 350 else ctx[:350] + "..."
            lines.append(f"**Context {idx}**")
            lines.append(f"> {preview.replace(chr(10), chr(10) + '> ')}")
            lines.append("")

    if getattr(response, "final_message", None) and response.final_message != response.answer:
        lines.append("")
        lines.append("## 💡 Note")
        lines.append("")
        lines.append(response.final_message)

    lines.append("")
    lines.append("**Meal memory:** not changed.")

    return "\n".join(lines)


def build_welcome_message() -> str:
    return (
        "# 🥗 Nutrition Assistant\n\n"
        "**Food & Nutrition AI**\n\n"
        "I can help you with:\n\n"
        "- **Calorie estimation** from food + grams\n"
        "- **Nutrition Q&A** using retrieved knowledge\n"
        "- **Semantic memory for repeated questions**\n"
        "- **Meal memory for calorie tracking**\n"
        "- **Simple and user-friendly answers**\n\n"
        "### Try one of these\n"
        "- `apple 200g`\n"
        "- `apple200g`\n"
        "- `apple 200g rice 150g`\n"
        "- `and banana 100g`\n"
        "- `What are good sources of protein?`\n"
        "- `Is avocado healthy?`\n\n"
        "> Please use English for food and nutrition queries."
    )


def serialize_meal_state(meal_state) -> dict:
    if meal_state is None:
        return {"error": "MealState is not available because imports failed."}

    return {
        "total_calories": getattr(meal_state, "total_calories", 0),
        "last_input": getattr(meal_state, "last_input", ""),
        "items": [
            {
                "food": item.food,
                "grams": item.grams,
                "calories": item.calories,
                "kcal_per_100g": item.kcal_per_100g,
            }
            for item in getattr(meal_state, "items", []) or []
        ],
    }


def serialize_response_object(response):
    try:
        return response.model_dump()
    except AttributeError:
        try:
            return response.dict()
        except AttributeError:
            try:
                return response.__dict__
            except Exception:
                return {"raw_response": str(response)}


def serialize_response_items(response):
    serialized_items = []

    for item in getattr(response, "items", []) or []:
        serialized_items.append(
            {
                "input_food": getattr(item, "input_food", None),
                "matched_food": getattr(item, "matched_food", None),
                "grams": getattr(item, "grams", None),
                "calories": getattr(item, "calories", None),
                "kcal_per_100g": getattr(item, "kcal_per_100g", None),
                "status": getattr(item, "status", None),
                "confidence": getattr(item, "confidence", None),
                "match_reason": getattr(item, "match_reason", None),
                "match_source": getattr(item, "match_source", None),
                "why_rejected": getattr(item, "why_rejected", None),
                "suggestions": getattr(item, "suggestions", None),
            }
        )

    return serialized_items


def to_debug_json(response, meal_state=None, extra: dict = None) -> str:
    response_payload = serialize_response_object(response)

    if hasattr(response, "items"):
        response_payload["items"] = serialize_response_items(response)

    payload = {
        "response": response_payload,
    }

    if meal_state is not None:
        payload["current_meal_memory"] = serialize_meal_state(meal_state)

    if extra:
        payload["extra"] = extra

    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def should_store_in_semantic_memory(response) -> bool:
    if getattr(response, "mode", "") != "nutrition_qa":
        return False

    if not hasattr(response, "answer"):
        return False

    answer = (getattr(response, "answer", "") or "").strip().lower()

    blocked_answers = {
        NON_ENGLISH_MESSAGE.lower(),
        EMPTY_MESSAGE.lower(),
        QUANTITY_ONLY_MESSAGE.lower(),
        NON_DIGIT_QUANTITY_MESSAGE.lower(),
        UNCLEAR_MESSAGE.lower(),
        "this assistant only handles food, calories, and nutrition.".lower(),
        FOOD_NOT_CONFIDENT_MESSAGE.lower(),
    }

    if answer in blocked_answers:
        return False

    if answer.startswith("i recognized '") and "but i still need the quantity in grams." in answer:
        return False

    return True


def get_conversation_memory():
    memory = cl.user_session.get("conversation_memory")
    if memory is None:
        memory = []
        cl.user_session.set("conversation_memory", memory)
    return memory


def build_clear_meal_response(meal_state):
    if meal_state is not None:
        meal_state.items = []
        meal_state.total_calories = 0
        meal_state.last_input = ""

    return SimpleNamespace(
        mode="calorie",
        items=[],
        total_calories=0,
        coverage="0/0",
        matched_items=0,
        total_items=0,
        confidence="HIGH",
        final_message="Your meal memory has been cleared.",
        suggestions=[],
    )


def build_remove_item_response(meal_state, target: str):
    items = getattr(meal_state, "items", []) or []
    kept_items = []
    removed_items = []

    for item in items:
        food_name = str(getattr(item, "food", "")).strip().lower()
        if target and target in food_name:
            removed_items.append(item)
        else:
            kept_items.append(item)

    meal_state.items = kept_items
    meal_state.total_calories = round(
        sum(float(getattr(x, "calories", 0) or 0) for x in kept_items),
        2,
    )

    if removed_items:
        message = f"I removed '{target}' from your meal memory."
        confidence = "HIGH"
    else:
        message = f"I could not find '{target}' in your meal memory."
        confidence = "MEDIUM"

    return SimpleNamespace(
        mode="calorie",
        items=[],
        total_calories=getattr(meal_state, "total_calories", 0),
        coverage=f"{len(kept_items)}/{len(kept_items)}" if kept_items else "0/0",
        matched_items=len(kept_items),
        total_items=len(kept_items),
        confidence=confidence,
        final_message=message,
        suggestions=[],
    )


async def ensure_orchestrator():
    global orchestrator

    if IMPORT_ERROR:
        raise RuntimeError(f"Import failed: {IMPORT_ERROR}")

    if orchestrator is None:
        orchestrator = NutritionOrchestrator()

    return orchestrator


async def show_error_state(thinking_message: cl.Message, error: Exception):
    meal_state = get_meal_state()

    error_payload = {
        "error": str(error),
        "type": type(error).__name__,
        "current_meal_memory": serialize_meal_state(meal_state),
        "traceback": traceback.format_exc(),
    }

    debug_json = json.dumps(error_payload, indent=2, ensure_ascii=False)
    set_last_debug_payload(debug_json)

    thinking_message.content = (
        "# ❌ Error\n\n"
        "An error occurred while processing your request.\n\n"
        "Use **Show Debug** to inspect the full error."
    )
    thinking_message.actions = get_debug_actions()
    thinking_message.elements = []
    await thinking_message.update()


async def handle_query(user_text: str, thinking_message: cl.Message):
    engine = await ensure_orchestrator()

    history = cl.user_session.get("history") or []
    memory_entries = cl.user_session.get("memory_entries") or []
    meal_state = get_meal_state()
    conversation_memory = get_conversation_memory()

    original_user_text = user_text
    normalized_user_text = normalize_text(user_text)
    normalized_command = normalize_command(original_user_text)

    if is_clear_meal_query(original_user_text):
        response = build_clear_meal_response(meal_state)

    elif get_remove_target(original_user_text):
        response = build_remove_item_response(meal_state, get_remove_target(original_user_text))

    else:
        response = engine.run(
            normalized_user_text,
            history=history,
            memory_entries=memory_entries,
            meal_state=meal_state,
            conversation_memory=conversation_memory,
        )

    mode = getattr(response, "mode", "")

    if mode == "calorie":
        formatted = format_calorie_response(response, meal_state=meal_state)
        assistant_text_for_memory = getattr(response, "final_message", formatted)
    else:
        formatted = format_qa_response(response)
        assistant_text_for_memory = getattr(response, "answer", formatted)

    debug_payload = to_debug_json(
        response,
        meal_state,
        extra={
            "normalized_user_text": normalized_user_text,
            "original_user_text": original_user_text,
            "normalized_command": normalized_command,
            "is_clear_meal_query": is_clear_meal_query(original_user_text),
            "remove_target": get_remove_target(original_user_text),
            "debug_enabled": is_debug_enabled(),
        },
    )

    set_last_debug_payload(debug_payload)

    thinking_message.content = formatted
    thinking_message.actions = get_debug_actions()
    thinking_message.elements = [build_debug_element(debug_payload)] if is_debug_enabled() else []
    await thinking_message.update()

    history.append({"role": "user", "content": original_user_text})
    history.append({"role": "assistant", "content": assistant_text_for_memory})
    cl.user_session.set("history", history[-30:])

    cl.user_session.set("meal_state", meal_state)
    save_conversation_turn(
        original_user_text=original_user_text,
        normalized_user_text=normalized_user_text,
        response=response,
        assistant_text=assistant_text_for_memory,
    )

    if should_store_in_semantic_memory(response) and MemoryEntry is not None:
        entry = MemoryEntry(
            question=normalized_user_text,
            answer=getattr(response, "answer", ""),
            mode="nutrition_qa",
            confidence=getattr(response, "confidence", "LOW"),
            sources_used=getattr(response, "sources_used", []) or [],
        )
        memory_entries.append(entry)
        cl.user_session.set("memory_entries", memory_entries[-20:])


def save_conversation_turn(original_user_text: str, normalized_user_text: str, response, assistant_text: str):
    memory = get_conversation_memory()
    mode = getattr(response, "mode", "unknown")

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": original_user_text,
        "normalized_input": normalized_user_text,
        "kind": mode,
        "assistant_text": assistant_text,
    }

    if mode == "calorie":
        record["total_calories"] = getattr(response, "total_calories", None)
        record["final_message"] = getattr(response, "final_message", "")
        items = []
        for item in getattr(response, "items", []) or []:
            items.append(
                {
                    "input_food": getattr(item, "input_food", None),
                    "matched_food": getattr(item, "matched_food", None),
                    "grams": getattr(item, "grams", None),
                    "calories": getattr(item, "calories", None),
                    "kcal_per_100g": getattr(item, "kcal_per_100g", None),
                    "status": getattr(item, "status", None),
                    "confidence": getattr(item, "confidence", None),
                    "match_reason": getattr(item, "match_reason", None),
                    "match_source": getattr(item, "match_source", None),
                    "why_rejected": getattr(item, "why_rejected", None),
                    "suggestions": getattr(item, "suggestions", None),
                }
            )
        record["items"] = items

    if hasattr(response, "answer"):
        record["answer"] = getattr(response, "answer", "")
        record["confidence"] = getattr(response, "confidence", "LOW")
        record["sources_used"] = getattr(response, "sources_used", []) or []
        record["retrieved_contexts"] = getattr(response, "retrieved_contexts", []) or []

    memory.append(record)
    cl.user_session.set("conversation_memory", memory[-50:])


@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    cl.user_session.set("memory_entries", [])
    cl.user_session.set("conversation_memory", [])
    cl.user_session.set("last_debug_payload", "")
    cl.user_session.set("debug_enabled", False)

    if MealState is not None:
        cl.user_session.set("meal_state", MealState())
    else:
        cl.user_session.set("meal_state", None)

    if IMPORT_ERROR:
        debug_payload = json.dumps(
            {
                "import_error": IMPORT_ERROR,
                "traceback": IMPORT_TRACEBACK,
            },
            indent=2,
            ensure_ascii=False,
        )
        set_last_debug_payload(debug_payload)

        await cl.Message(
            content=(
                "# ❌ Startup Import Error\n\n"
                "The app loaded, but one of the project imports failed.\n\n"
                "Press **Show Debug** to inspect the error."
            ),
            actions=get_debug_actions(),
        ).send()
        return

    actions = [
        cl.Action(name="example_apple", label="apple 200g", payload={"query": "apple 200g"}),
        cl.Action(name="example_compact", label="apple200g", payload={"query": "apple200g"}),
        cl.Action(name="example_multi", label="apple 200g rice 150g", payload={"query": "apple 200g rice 150g"}),
        cl.Action(name="example_banana", label="and banana 100g", payload={"query": "and banana 100g"}),
        cl.Action(
            name="example_qa",
            label="What are good sources of protein?",
            payload={"query": "What are good sources of protein?"},
        ),
    ] + get_debug_actions()

    await cl.Message(
        content=build_welcome_message(),
        actions=actions,
    ).send()


@cl.action_callback("toggle_debug")
async def on_toggle_debug(action: cl.Action):
    set_debug_enabled(not is_debug_enabled())
    status = "enabled" if is_debug_enabled() else "disabled"
    await cl.Message(content=f"Debug mode is now **{status}**.").send()


@cl.action_callback("show_debug")
async def on_show_debug(action: cl.Action):
    debug_payload = get_last_debug_payload()

    if not debug_payload:
        await cl.Message(content="No debug is available yet. Send a query first.").send()
        return

    await cl.Message(
        content="# 🧠 Debug loaded in side panel",
        elements=[build_debug_element(debug_payload)],
    ).send()


@cl.action_callback("example_apple")
@cl.action_callback("example_compact")
@cl.action_callback("example_multi")
@cl.action_callback("example_banana")
@cl.action_callback("example_qa")
async def on_example_action(action: cl.Action):
    query = action.payload["query"]

    await cl.Message(content=f"`{query}`", author="You").send()

    thinking = cl.Message(content="⏳ Processing your request...")
    await thinking.send()

    try:
        await handle_query(query, thinking)
    except Exception as e:
        await show_error_state(thinking, e)


@cl.on_message
async def main(message: cl.Message):
    user_text = (message.content or "").strip()

    if not user_text:
        await cl.Message(
            content=(
                "# 🥗 Nutrition Assistant\n\n"
                "Please enter an **English food query** or an **English nutrition question**.\n\n"
                "### Examples\n"
                "- `apple 200g`\n"
                "- `apple200g`\n"
                "- `apple 200g rice 150g`\n"
                "- `and banana 100g`\n"
                "- `Is avocado healthy?`"
            ),
            actions=get_debug_actions(),
        ).send()
        return

    thinking = cl.Message(content="⏳ Processing your request...")
    await thinking.send()

    try:
        await handle_query(user_text, thinking)
    except Exception as e:
        await show_error_state(thinking, e)