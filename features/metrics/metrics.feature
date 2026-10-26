@metrics
Feature: Metrics
  As an operator
  I want each agent to report how it is performing when I ask it to
  So that I can watch latency, failures, and token use without affecting travelers

  @TP-SRS-120
  Scenario: Metrics are exported when an OTLP endpoint is set
    Given OTEL_EXPORTER_OTLP_ENDPOINT is set
    And the Activities agent is running with retrieval enabled
    When I post a valid travel request to the Activities agent
    And metrics are collected
    Then they include HTTP request metrics for "/run"
    And they include the model call duration with its outcome
    And they include token usage by type
    And they include the retrieval duration with its outcome
    And metrics are exported at least once a minute

  @TP-SRS-120
  Scenario Outline: Model call durations are labelled by outcome
    Given OTEL_EXPORTER_OTLP_ENDPOINT is set
    And the language model <behaviour>
    When I post a valid travel request to the Flight agent
    Then a model call duration is recorded with outcome "<outcome>"

    Examples:
      | behaviour                                | outcome |
      | answers normally                         | success |
      | returns status 500                       | error   |
      | takes longer than LLM_TIMEOUT_SECONDS    | timeout |

  @TP-SRS-121
  Scenario: No metrics are sent when no OTLP endpoint is set
    Given OTEL_EXPORTER_OTLP_ENDPOINT is not set
    When I post a valid travel request to the Host
    Then no metrics are sent

  @TP-SRS-122
  Scenario: A metrics export failure does not affect requests
    Given OTEL_EXPORTER_OTLP_ENDPOINT is set
    And the metrics endpoint rejects every export
    When I post a valid travel request to the Host
    Then the response status is 200
    And the export failure is logged
