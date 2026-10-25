@api @specialist
Feature: Suggestion generation
  As a traveler
  I want each specialist to give well-formed, honest suggestions or a clear error
  So that what I see is either valid or plainly marked as failed

  Background:
    Given retrieval is disabled

  @TP-SRS-070 @TP-SRS-072
  Scenario Outline: A valid model answer becomes offers
    Given the <agent> agent is running
    And the language model answers with valid <agent> offers
    When I post a valid travel request to the <agent> agent
    Then the response has at least one offer
    And every offer matches the <agent> response model

    Examples:
      | agent      |
      | Flight     |
      | Stay       |
      | Activities |

  @TP-SRS-071
  Scenario Outline: The model is asked for schema-constrained JSON at temperature 0
    Given LLM_PROVIDER is "<provider>"
    And the <agent> agent is running
    When I post a valid travel request to the <agent> agent
    Then the language-model request asks for JSON matching the <agent> response schema
    And the language-model request sets temperature to 0

    Examples:
      | provider | agent      |
      | ollama   | Flight     |
      | ollama   | Stay       |
      | ollama   | Activities |
      | openai   | Flight     |
      | openai   | Stay       |
      | openai   | Activities |

  @TP-SRS-070 @TP-SRS-072 @TP-SRS-073 @TP-SRS-074 @TP-SRS-132
  Scenario Outline: Model failures give a plain error and log the cause
    Given the <agent> agent is running
    And the language model <failure>
    When I post a valid travel request to the <agent> agent
    Then the response error is "<message>"
    And the response mentions no provider name, stack trace, or key
    And the agent logs the underlying cause

    Examples:
      | agent      | failure                                          | message                                      |
      | Flight     | returns status 500                               | Flight planner is temporarily unavailable.   |
      | Stay       | takes longer than LLM_TIMEOUT_SECONDS            | Stay planner is temporarily unavailable.     |
      | Activities | refuses the request                              | Activity planner is temporarily unavailable. |
      | Flight     | answers with text that is not JSON               | Flight planner is temporarily unavailable.   |
      | Stay       | answers with an offer priced at -10              | Stay planner is temporarily unavailable.     |
      | Activities | answers with an offer in currency "US"           | Activity planner is temporarily unavailable. |
      | Flight     | answers with no offers and no error              | Flight planner is temporarily unavailable.   |

  @TP-SRS-075
  Scenario Outline: The prompt tells the model the suggestions are not live or bookable
    Given the <agent> agent is running
    When I post a valid travel request to the <agent> agent
    Then the prompt tells the model not to present suggestions as live or bookable

    Examples:
      | agent      |
      | Flight     |
      | Stay       |
      | Activities |

  @TP-SRS-076
  Scenario: The Activities agent uses the traveler's preferences
    Given the Activities agent is running
    When I post a valid travel request with preferences "museums" and "street food"
    Then the prompt includes "museums" and "street food"

  @TP-SRS-076
  Scenario: The Activities agent falls back to general sightseeing
    Given the Activities agent is running
    When I post a valid travel request without preferences
    Then the prompt includes "general sightseeing"

  @TP-SRS-077 @TP-SRS-186
  Scenario Outline: The model provider is chosen by configuration
    Given LLM_PROVIDER is "<provider>"
    And the Flight agent is running
    When I post a valid travel request to the Flight agent
    Then the model request goes to <endpoint>

    Examples:
      | provider | endpoint                          |
      | ollama   | the Ollama chat endpoint          |
      | openai   | the OpenAI chat completions endpoint |
