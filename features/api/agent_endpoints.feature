@api
Feature: Agent service endpoints
  As an API client or operator
  I want every agent to offer the same basic endpoints
  So that I can call, monitor, and inspect any of them in the same way

  @TP-SRS-001 @TP-SRS-006
  Scenario Outline: Every agent exposes the standard endpoints
    Given the <agent> agent is running
    Then it exposes these endpoints:
      | method | path          |
      | POST   | /run          |
      | GET    | /healthz      |
      | GET    | /readyz       |
      | GET    | /             |
      | GET    | /openapi.json |

    Examples:
      | agent      |
      | Host       |
      | Flight     |
      | Stay       |
      | Activities |

  @TP-SRS-002
  Scenario Outline: The health check reports the service
    Given the <agent> agent is running
    When I request "GET /healthz"
    Then the response status is 200
    And the response body is:
      """json
      {"status": "ok", "service": "<service>"}
      """

    Examples:
      | agent      | service    |
      | Host       | host       |
      | Flight     | flight     |
      | Stay       | stay       |
      | Activities | activities |

  @TP-SRS-002
  Scenario: The health check never needs an API key
    Given the Host is running with HOST_API_KEY set to "s3cret"
    When I request "GET /healthz" without an "X-API-Key" header
    Then the response status is 200

  @TP-SRS-006
  Scenario: The OpenAPI schema describes the run endpoint
    Given the Host is running
    When I request "GET /openapi.json"
    Then the response status is 200
    And the schema describes "POST /run"

  @TP-SRS-004
  Scenario Outline: An invalid request body is rejected with the invalid fields listed
    Given the <agent> agent is running
    When I post this body to "/run":
      """json
      {"origin": "M", "destination": "Tokyo", "start_date": "2026-12-01",
       "end_date": "2026-12-06", "budget": 1500, "travellers": 12}
      """
    Then the response status is 422
    And the response lists the invalid fields "origin" and "travellers"

    Examples:
      | agent      |
      | Host       |
      | Flight     |
      | Stay       |
      | Activities |

  @TP-SRS-005
  Scenario: A request ID is logged and forwarded to every specialist
    Given the Host and the specialists are running
    When I post a valid travel request to the Host with the header "X-Request-ID: trip-test-001"
    Then the Host's log lines for the request include "trip-test-001"
    And the Flight, Stay, and Activities agents each receive the header "X-Request-ID: trip-test-001"
    And each specialist's log lines for the request include "trip-test-001"
