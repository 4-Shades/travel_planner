@api @host
Feature: Travel request validation
  As an API client
  I want the Host to check and tidy my travel request
  So that I get a clear error for bad input and consistent results for good input

  Background:
    Given the Host is running
    And the specialists answer normally

  @TP-SRS-050
  Scenario Outline: Place names must be 2 to 120 characters long
    When I post a valid travel request with a <field> of <length> characters
    Then the response status is <status>

    Examples:
      | field       | length | status |
      | origin      | 1      | 422    |
      | origin      | 2      | 200    |
      | origin      | 120    | 200    |
      | origin      | 121    | 422    |
      | destination | 1      | 422    |
      | destination | 2      | 200    |
      | destination | 120    | 200    |
      | destination | 121    | 422    |

  @TP-SRS-050
  Scenario Outline: The end date must be after the start date
    When I post a valid travel request with start date "2026-12-06" and end date "<end date>"
    Then the response status is <status>

    Examples:
      | end date   | status |
      | 2026-12-05 | 422    |
      | 2026-12-06 | 422    |
      | 2026-12-07 | 200    |

  @TP-SRS-050 @TP-SRS-172
  Scenario Outline: Field values outside their limits are rejected
    When I post a valid travel request with "<field>" set to <value>
    Then the response status is 422
    And the response lists the invalid field "<field>"

    Examples:
      | field      | value        |
      | budget     | 0            |
      | budget     | -50          |
      | travellers | 0            |
      | travellers | 10           |
      | currency   | "US"         |
      | currency   | "USDD"       |
      | currency   | "U5D"        |
      | start_date | "01/12/2026" |

  @TP-SRS-050
  Scenario Outline: Values at the edge of their limits are accepted
    When I post a valid travel request with "<field>" set to <value>
    Then the response status is 200

    Examples:
      | field      | value  |
      | budget     | 0.01   |
      | travellers | 1      |
      | travellers | 9      |
      | currency   | "JPY"  |

  @TP-SRS-050
  Scenario Outline: Preferences and user ID have length limits
    When I post a valid travel request with <amount>
    Then the response status is <status>

    Examples:
      | amount                           | status |
      | 20 preferences                   | 200    |
      | 21 preferences                   | 422    |
      | a user_id of 128 characters      | 200    |
      | a user_id of 129 characters      | 422    |

  @TP-SRS-051
  Scenario: Repeated spaces are collapsed and the currency is upper-cased
    When I post a valid travel request with origin "San   Francisco", destination "New    York City", and currency "eur"
    Then each specialist receives origin "San Francisco"
    And each specialist receives destination "New York City"
    And each specialist receives currency "EUR"

  @TP-SRS-052
  Scenario: Missing request and trip IDs are generated
    When I post a valid travel request without a request_id or trip_id
    Then the plan's request_id is a UUID
    And the plan's trip_id is a UUID

  @TP-SRS-052
  Scenario: Given request and trip IDs are kept
    When I post a valid travel request with request_id "req-42" and trip_id "trip-42"
    Then the plan's request_id is "req-42"
    And the plan's trip_id is "trip-42"

  @TP-SRS-053
  Scenario: The currency defaults to US dollars
    When I post a valid travel request without a currency
    Then each specialist receives currency "USD"
