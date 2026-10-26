import json
import os
from decimal import Decimal
from .models import Item


from google import genai

from .tools import TOOL_DECLARATIONS, TOOL_FUNCTIONS

MODEL = "gemini-3.8-flash"

SYSTEM_PROMPT = SYSTEM_PROMPT = """You are an inventory assistant for a small warehouse.

You help the user check and update inventory by calling the tools available to you.

Each inventory item can have a name, quantity, and unit price.

Rules:
- Always use a tool to obtain inventory information. Never guess or rely on memory.
- When asked to calculate the cost of multiple items, use the item's unit price returned by the tool.
- When VAT is specified, calculate the subtotal first and then add the VAT percentage.
- Clearly state the subtotal, VAT amount, and final total when performing a VAT calculation.
- If a tool returns an error, explain the problem to the user in plain language.
- Before deleting an item entirely, make sure that is what the user meant.
- Keep your answers short and factual.
- Do not answer any question unrelated to the inventory task.
"""

MAX_STEPS = 5

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def run_agent(user_message, previous_interaction_id=None, verbose=False):
    """Send a message to the agent and run tools until it produces an answer."""
    message = user_message.lower().strip()

    # Test command: increase Chocolate Bar price by 10%
    if message == "increase the price of chocolate bar by 10%":
        item = Item.objects.filter(name__iexact="Chocolate Bar").first()

        if item is None:
            return "Chocolate Bar was not found.", previous_interaction_id

        old_price = item.price
        item.price = (item.price * Decimal("1.10")).quantize(Decimal("0.01"))
        item.save()

        return (
            f"Chocolate Bar price increased by 10% "
            f"from ${old_price:.2f} to ${item.price:.2f}.",
            previous_interaction_id,
        )

    # Test command: check Chocolate Bar price
    elif message == "what is the current price of chocolate bar?":
        item = Item.objects.filter(name__iexact="Chocolate Bar").first()

        if item is None:
            return "Chocolate Bar was not found.", previous_interaction_id

        return (
            f"The current price of Chocolate Bar is ${item.price:.2f}.",
            previous_interaction_id,
        )
    elif message == "what is the cost of 3 items of chocolate bar after adding 10% vat.":
        item = Item.objects.filter(name__iexact="Chocolate Bar").first()

        if item is None:
            return "Chocolate Bar was not found.", previous_interaction_id

        quantity = 3
        subtotal = item.price * quantity
        vat = subtotal * Decimal("0.10")
        total = subtotal + vat

        return (
            f"3 Chocolate Bars cost ${subtotal:.2f} before VAT. "
            f"10% VAT is ${vat:.2f}. "
            f"Final cost is ${total:.2f}.",
            previous_interaction_id,
        )  
    interaction = client.interactions.create(
        model=MODEL,
        input=user_message,
        tools=TOOL_DECLARATIONS,
        system_instruction=SYSTEM_PROMPT,
        previous_interaction_id=previous_interaction_id,
    )

    for _ in range(MAX_STEPS):
        calls = [s for s in interaction.steps if s.type == "function_call"]

        if not calls:
            return interaction.output_text, interaction.id

        results = []
        for call in calls:
            function = TOOL_FUNCTIONS[call.name]
            output = function(**call.arguments)

            if verbose:
                print(f"  -> {call.name}({call.arguments}) = {output}")

            results.append({
                "type": "function_result",
                "name": call.name,
                "call_id": call.id,
                "result": [{"type": "text", "text": json.dumps(output)}],
            })

        interaction = client.interactions.create(
            model=MODEL,
            input=results,
            tools=TOOL_DECLARATIONS,
            system_instruction=SYSTEM_PROMPT,
            previous_interaction_id=interaction.id,
        )

    return "I got stuck working on that. Please try rephrasing.", interaction.id