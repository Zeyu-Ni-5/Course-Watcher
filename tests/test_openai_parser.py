from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)

from app.errors import (
    ConfigurationError,
    ModelResponseInvalidError,
    ModelServiceError,
)
from app.parsing.openai_parser import (
    OpenAICourseRequestParser,
    create_openai_parser,
)
from app.schemas import ModelCourseFields
from app.settings import ParseSettings


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.response


class FakeOpenAIClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response, error)


def parsed_response():
    return SimpleNamespace(
        output_parsed=ModelCourseFields(
            subject="CS",
            catalog="136",
            component="LEC",
            term_season="FALL",
            term_year=2026,
        )
    )


def test_openai_parser_uses_luna_structured_outputs():
    client = FakeOpenAIClient(response=parsed_response())
    parser = OpenAICourseRequestParser(
        client=client,
        model_name="gpt-5.6-luna",
    )

    result = parser.parse("Watch CS 136 lectures in Fall 2026")

    assert result["subject"] == "CS"
    call = client.responses.calls[0]
    assert call["model"] == "gpt-5.6-luna"
    assert call["reasoning"] == {"effort": "none"}
    assert call["text_format"] is ModelCourseFields
    assert call["store"] is False
    assert call["input"][0]["role"] == "system"
    assert call["input"][1] == {
        "role": "user",
        "content": "Watch CS 136 lectures in Fall 2026",
    }


def test_openai_parser_adds_internal_repair_feedback():
    client = FakeOpenAIClient(response=parsed_response())
    parser = OpenAICourseRequestParser(
        client=client,
        model_name="gpt-5.6-luna",
    )

    parser.parse(
        "Watch CS 136",
        feedback="term_season: invalid value",
    )

    system_text = client.responses.calls[0]["input"][0]["content"]
    assert "term_season: invalid value" in system_text


def test_openai_parser_rejects_absent_parsed_output():
    client = FakeOpenAIClient(
        response=SimpleNamespace(output_parsed=None)
    )
    parser = OpenAICourseRequestParser(
        client=client,
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(ModelResponseInvalidError):
        parser.parse("Watch CS 136")


def test_create_openai_parser_requires_api_key():
    settings = ParseSettings(
        app_access_token="token",
        openai_api_key=None,
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(ConfigurationError):
        create_openai_parser(settings)


def test_create_openai_parser_configures_client(monkeypatch):
    configured_client = object()
    calls = []

    def fake_openai(**kwargs):
        calls.append(kwargs)
        return configured_client

    monkeypatch.setattr(
        "app.parsing.openai_parser.OpenAI",
        fake_openai,
    )
    settings = ParseSettings(
        app_access_token="token",
        openai_api_key="api-key",
        model_name="settings-selected-model",
    )

    parser = create_openai_parser(settings)

    assert calls == [
        {
            "api_key": "api-key",
            "timeout": 10.0,
            "max_retries": 0,
        }
    ]
    assert parser.client is configured_client
    assert parser.model_name == "settings-selected-model"


def sdk_errors():
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )

    return [
        APITimeoutError(request=request),
        APIConnectionError(request=request),
        RateLimitError(
            "rate limited",
            response=httpx.Response(429, request=request),
            body=None,
        ),
        AuthenticationError(
            "bad API key",
            response=httpx.Response(401, request=request),
            body=None,
        ),
    ]


@pytest.mark.parametrize("sdk_error", sdk_errors())
def test_openai_parser_sanitizes_sdk_errors(sdk_error):
    client = FakeOpenAIClient(error=sdk_error)
    parser = OpenAICourseRequestParser(
        client=client,
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(ModelServiceError) as error:
        parser.parse("Watch CS 136")

    assert str(error.value) == (
        "The model service could not parse the request."
    )
    assert str(sdk_error) not in str(error.value)


def test_openai_parser_sanitizes_base_sdk_error():
    sdk_error = OpenAIError("raw provider detail")
    client = FakeOpenAIClient(error=sdk_error)
    parser = OpenAICourseRequestParser(
        client=client,
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(ModelServiceError) as error:
        parser.parse("Watch CS 136")

    assert str(error.value) == (
        "The model service could not parse the request."
    )
    assert "raw provider detail" not in str(error.value)
