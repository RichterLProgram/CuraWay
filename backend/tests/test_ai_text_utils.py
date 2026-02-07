"""Tests for features/ai/text_utils.py"""

from features.ai.text_utils import split_sentences


def test_split_sentences_empty():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_split_sentences_with_punctuation():
    text = "Hello world.  Next? Final!"
    assert split_sentences(text) == ["Hello world.", "Next?", "Final!"]


def test_split_sentences_without_punctuation():
    text = "Single sentence without punctuation"
    assert split_sentences(text) == [text]
