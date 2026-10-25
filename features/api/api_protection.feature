@api @host
Feature: API protection
  As an operator
  I want the public Host API to require a key when I configure one
  So that only my clients can use the planner

  @TP-SRS-110
  Scenario Outline: A key is required when HOST_API_KEY is set
    Given the Host is running with HOST_API_KEY set to "s3cret"
    And the specialists answer normally
    When I post a valid travel request <header>
    Then the response status is <status>

    Examples:
      | header                              | status |
      | without an "X-API-Key" header       | 401    |
      | with the header "X-API-Key: wrong"  | 401    |
      | with the header "X-API-Key: s3cret" | 200    |

  @TP-SRS-110
  Scenario: A missing key is reported before the body is checked
    Given the Host is running with HOST_API_KEY set to "s3cret"
    When I post an invalid travel request without an "X-API-Key" header
    Then the response status is 401

  @TP-SRS-110 @TP-SRS-132
  Scenario: A rejected request does not reveal the key
    Given the Host is running with HOST_API_KEY set to "s3cret"
    When I post a valid travel request with the header "X-API-Key: wrong"
    Then the response body does not contain "s3cret"

  @TP-SRS-112
  Scenario: No key is needed when HOST_API_KEY is not set
    Given the Host is running without HOST_API_KEY
    And the specialists answer normally
    When I post a valid travel request without an "X-API-Key" header
    Then the response status is 200

  @deployment @TP-SRS-113 @TP-SRS-165 @TP-SRS-184
  Scenario: Only the web application and the Host are public
    Given the application is deployed to Vercel
    When I send requests from outside the deployment to each service address
    Then the web application and the Host answer over HTTPS
    And requests to the Flight, Stay, and Activities agents fail
    And plain HTTP requests are redirected to HTTPS or refused
