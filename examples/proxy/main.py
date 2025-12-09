"""
Pokemon Proxy Example - Gotta Catch 'Em All! 🎮

Demonstrates API proxy functionality by fetching Pokemon data.
"""

import datetime

from pyscript import fetch, web, when


def capitalize_words(text):
    """
    Capitalize each word in text (MicroPython compatible).

    Uses only slicing and upper() which are available in MicroPython.
    """
    words = text.split()
    capitalized = []
    for word in words:
        if len(word) > 0:
            # Capitalize first letter, keep rest lowercase.
            capitalized.append(word[0].upper() + word[1:].lower())
    return " ".join(capitalized)


def log_request(message, style="info"):
    """
    Add a log message to the request log with playful styling.
    """
    log_container = web.page.find("#request-log")[0]

    # Create log entry with timestamp.
    timestamp = web.span(f"[{get_timestamp()}]", className=f"log-timestamp")

    log_entry = web.div(
        timestamp,
        web.span(f" {message}", className=f"log-message log-{style}"),
        className="log-entry",
    )

    log_container.append(log_entry)

    # Auto-scroll to bottom.
    log_container._dom_element.scrollTop = (
        log_container._dom_element.scrollHeight
    )


def get_timestamp():
    """
    Get current time as string.
    """
    return str(datetime.datetime.now())


def clear_card():
    """
    Clear the Pokemon card display.
    """
    card = web.page.find("#pokemon-card")[0]
    card.innerHTML = ""


def show_error(pokemon_name):
    """
    Display a playful error message when Pokemon not found.
    """
    card = web.page.find("#pokemon-card")[0]
    card.innerHTML = ""

    error_content = web.div(
        web.div("🤔", className="error-emoji"),
        web.h2(f"Oops! No '{pokemon_name}' in the Pokédex!"),
        web.p("Maybe you misspelled it? Try again, Trainer!"),
        web.p(
            "💡 Hint: Try classics like 'pikachu', 'charizard', or 'mewtwo'",
            className="hint",
        ),
        className="error-message",
    )

    card.append(error_content)


def display_pokemon(data):
    """
    Display a playful Pokemon card with all the fun details!
    """
    card = web.page.find("#pokemon-card")[0]
    card.innerHTML = ""

    # Defensive data extraction.
    name = data.get("name", "Unknown")
    if isinstance(name, str) and len(name) > 0:
        # Capitalize first letter (MicroPython compatible).
        name = name[0].upper() + name[1:].lower()

    pokemon_id = data.get("id", 0)
    height = data.get("height", 0) / 10  # Convert to meters.
    weight = data.get("weight", 0) / 10  # Convert to kg.

    # Get types with fun emoji.
    type_emoji = {
        "normal": "⚪",
        "fire": "🔥",
        "water": "💧",
        "electric": "⚡",
        "grass": "🌿",
        "ice": "❄️",
        "fighting": "👊",
        "poison": "☠️",
        "ground": "⛰️",
        "flying": "🦅",
        "psychic": "🔮",
        "bug": "🐛",
        "rock": "🪨",
        "ghost": "👻",
        "dragon": "🐉",
        "dark": "🌙",
        "steel": "⚙️",
        "fairy": "✨",
    }

    types = data.get("types", [])
    type_badges = []
    for t in types:
        type_name = t["type"]["name"]
        # Capitalize first letter (MicroPython compatible).
        if len(type_name) > 0:
            type_name_cap = type_name[0].upper() + type_name[1:].lower()
        else:
            type_name_cap = type_name
        emoji_char = type_emoji.get(type_name, "❓")
        badge = web.span(className=f"type-badge type-{type_name}")
        badge.append(
            web.span(emoji_char, className="type-emoji")
        )  # Emoji in circle
        badge.append(web.span(type_name_cap))  # Type name
        type_badges.append(badge)

    # Get sprite images.
    sprites = data.get("sprites", {})
    front_sprite = sprites.get("front_default", "")
    back_sprite = sprites.get("back_default", "")

    # Get cries (sounds).
    cries = data.get("cries", {})
    cry_latest = cries.get("latest", "")

    # Get some fun stats.
    stats = data.get("stats", [])
    stat_elements = []
    for stat in stats[:3]:  # Show first 3 stats.
        stat_name = capitalize_words(stat["stat"]["name"].replace("-", " "))
        stat_value = stat["base_stat"]
        stat_bar_width = min(stat_value / 2, 100)  # Scale for display.

        stat_elements.append(
            web.div(
                web.span(f"{stat_name}: ", className="stat-name"),
                web.span(str(stat_value), className="stat-value"),
                web.div(
                    web.div(
                        style={"width": f"{stat_bar_width}%"},
                        className="stat-bar-fill",
                    ),
                    className="stat-bar",
                ),
                className="stat-row",
            )
        )

    # Build the card!
    card_content = web.div(
        # Header with ID badge.
        web.div(
            web.span(f"#{pokemon_id:03d}", className="pokemon-id"),
            web.h1(f"✨ {name} ✨", className="pokemon-name"),
            className="card-header",
        ),
        # Types.
        web.div(*type_badges, className="types-container"),
        # Sprites.
        web.div(
            (
                web.div(
                    web.img(src=front_sprite, alt=f"{name} front"),
                    web.div("Front", className="sprite-label"),
                    className="sprite-box",
                )
                if front_sprite
                else web.div()
            ),
            (
                web.div(
                    web.img(src=back_sprite, alt=f"{name} back"),
                    web.div("Back", className="sprite-label"),
                    className="sprite-box",
                )
                if back_sprite
                else web.div()
            ),
            className="sprites-container",
        ),
        # Cry audio.
        web.div(
            web.h3("🔊 Hear me roar!"),
            (
                web.audio(
                    web.source(src=cry_latest, type_="audio/ogg"),
                    controls=True,
                )
                if cry_latest
                else web.p("(No cry available)", className="hint")
            ),
            className="cry-section",
        ),
        # Physical stats.
        web.div(
            web.div(
                web.span("📏 Height", className="physical-label"),
                web.span(f"{height}m", className="physical-value"),
                className="physical-stat",
            ),
            web.div(
                web.span("⚖️ Weight", className="physical-label"),
                web.span(f"{weight}kg", className="physical-value"),
                className="physical-stat",
            ),
            className="physical-stats",
        ),
        # Battle stats.
        web.div(
            web.h3("⚔️ Battle Stats"), *stat_elements, className="stats-section"
        ),
        className="pokemon-card-content",
    )

    card.append(card_content)


@when("click", "#search-button")
async def handle_search(event):
    """
    Search for a Pokemon by name!
    """
    input_field = web.page.find("#pokemon-input")[0]
    pokemon_name = input_field.value.strip().lower()

    if not pokemon_name:
        log_request("⚠️ Please enter a Pokemon name!", "warning")
        return

    # Clear previous results.
    clear_card()

    # Show loading state.
    card = web.page.find("#pokemon-card")[0]
    card.innerHTML = ""
    card.append(
        web.div(
            web.div("🔄", className="loading-spinner"),
            web.p("Searching the Pokédex..."),
            className="loading-message",
        )
    )

    # Log the request.
    log_request(f"🔍 Searching for '{pokemon_name}'...", "info")
    log_request(f"📡 GET /proxy/pokeapi/pokemon/{pokemon_name}", "request")

    try:
        # Make request through proxy.
        response = await fetch(
            f"/proxy/pokeapi/pokemon/{pokemon_name}", method="GET"
        )

        if response.status == 404:
            log_request(
                f"❌ 404 Not Found - '{pokemon_name}' doesn't exist!", "error"
            )
            show_error(pokemon_name)
        elif response.status == 200:
            data = await response.json()

            # Defensive check - ensure data is a dict.
            if isinstance(data, str):
                log_request(f"⚠️ Received string instead of JSON", "error")
                card.innerHTML = (
                    "<p class='error-message'>Error parsing response</p>"
                )
                return

            # Get pokemon name safely and capitalize it.
            pokemon_found = data.get("name", pokemon_name)
            if isinstance(pokemon_found, str) and len(pokemon_found) > 0:
                # Capitalize first letter (MicroPython compatible).
                pokemon_found = (
                    pokemon_found[0].upper() + pokemon_found[1:].lower()
                )

            log_request(f"✅ 200 OK - Found {pokemon_found}!", "success")
            display_pokemon(data)
        else:
            log_request(
                f"⚠️ {response.status} - Unexpected response", "warning"
            )
            card.innerHTML = f"<p>Unexpected response: {response.status}</p>"

    except Exception as e:
        log_request(f"💥 Error: {str(e)}", "error")
        card.innerHTML = f"<p class='error-message'>Error: {str(e)}</p>"


@when("keydown", "#pokemon-input")
async def handle_keydown(event):
    """
    Search when Enter is pressed.
    """
    if event.key == "Enter":
        await handle_search(event)


@when("click", "#clear-log-button")
def clear_log(event):
    """
    Clear the request log.
    """
    log_container = web.page.find("#request-log")[0]
    log_container.innerHTML = ""
    log_request("🧹 Log cleared!", "info")


# Welcome message!
print("🎮 Pokemon Proxy Example loaded!")
print("👾 Enter a Pokemon name to see their card!")
log_request("🌟 Welcome, Trainer! Ready to explore?", "info")
