from app.services.ai_service import AIService


def test_number_validation_never_supplies_a_fallback() -> None:
    assert AIService._number(42, 0, 100) == 42.0
    assert AIService._number(-0.5, -1, 1) == -0.5
    assert AIService._number(None, 0, 100) is None
    assert AIService._number("50", 0, 100) is None
    assert AIService._number(True, 0, 100) is None
    assert AIService._number(101, 0, 100) is None


def test_strategic_display_types_are_explicitly_bounded() -> None:
    assert "HOTSPOT" in AIService.DISPLAY_TYPES
    assert "UNKNOWN" not in AIService.DISPLAY_TYPES
