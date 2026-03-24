from __future__ import annotations

from application.services.memory_chat_transcript import MemoryChatTranscript


def test_memory_chat_transcript_round_trip() -> None:
    t = MemoryChatTranscript()
    t.init("p1")
    t.add_user_message("hi")
    t.add_assistant_message("hello")
    assert len(t.get_messages()) == 2
    t.init("p1")
    assert len(t.get_messages()) == 2
    t.init("p2")
    assert t.get_messages() == []
