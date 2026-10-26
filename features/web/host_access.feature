@web
Feature: Server-side access to the Host
  As an operator
  I want the web application to call the Host only from its server
  So that the Host address and API key never reach a browser

  @TP-SRS-040 @TP-SRS-041
  Scenario: Trip requests reach the Host through the web server
    Given HOST_SERVICE_URL points at the planning service
    And I open the travel planner
    When I submit a valid trip
    Then the planning service receives the trip at "/run"
    And my browser sends no request to the planning service's address

  @TP-SRS-043
  Scenario: The API key is sent to the Host when it is configured
    Given HOST_API_KEY is set to "test-key-123"
    When I submit a valid trip
    Then the planning service receives the header "X-API-Key: test-key-123"

  @TP-SRS-043
  Scenario: No API key is sent when none is configured
    Given HOST_API_KEY is not set
    When I submit a valid trip
    Then the planning service receives no "X-API-Key" header

  @TP-SRS-042
  Scenario Outline: The API key never reaches the browser
    Given the web application was built and started with HOST_API_KEY set to "sentinel-9f2c"
    And the planning service <behaviour>
    When I open the travel planner and submit a valid trip
    Then "sentinel-9f2c" appears in no page, script, or response my browser receives

    Examples:
      | behaviour                 |
      | returns a complete plan   |
      | returns status 401        |
      | returns status 500        |
