Feature: Performance
  As a traveler
  I want plans to arrive quickly and no request to be cut off early
  So that I am not left waiting or shown a failure that was only a slow part

  @demonstration @deployment @TP-SRS-140
  Scenario: Cloud plans arrive quickly with OpenAI
    Given the application is deployed to Vercel with OpenAI
    When I post a valid travel request to a warm Host
    Then the plan arrives within 10 seconds
    When I post a valid travel request to a Host that has just started
    Then the plan arrives within 30 seconds

  @api @TP-SRS-142
  Scenario Outline: Timeouts must nest
    Given LLM_TIMEOUT_SECONDS is <llm>
    And DOWNSTREAM_TIMEOUT_SECONDS is <downstream>
    When the Host starts
    Then the configuration is <result>

    Examples:
      | llm | downstream | result   |
      | 60  | 90         | accepted |
      | 60  | 60         | rejected |
      | 60  | 45         | rejected |
      | 60  | 180        | rejected |

  @demonstration @TP-SRS-144
  Scenario: Self-hosted models stay loaded
    Given the self-hosted stack is running with Ollama
    When I plan a trip
    And 25 minutes pass without a request
    Then the chat and embedding models are both still loaded
