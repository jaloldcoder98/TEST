"""English strings for the bot. Mirrored by ru.py and uz.py — never a hardcoded string inline
in a handler (spec.md §21). Phase 6 will likely move this to proper gettext/.ftl catalogs; a
plain dict is enough for the Phase 2 skeleton."""

STRINGS = {
    "welcome": "Welcome to your GYM AI Coach! Choose your language to continue.",
    "menu.workout": "🏋️ Workout",
    "menu.exercises": "💪 Exercises",
    "menu.progress": "📊 Progress",
    "menu.nutrition": "🍎 Nutrition",
    "menu.ai_coach": "🤖 AI Coach",
    "menu.profile": "👤 Profile",
    "menu.settings": "⚙️ Settings",
}
