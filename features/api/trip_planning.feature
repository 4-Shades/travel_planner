@api @host
Feature: Trip planning
  As a traveler or API client
  I want the Host to combine the three specialists' answers into one plan
  So that I get as much of a plan as possible, quickly, even when a part fails

  Background:
    Given the Host is running with DOWNSTREAM_TIMEOUT_SECONDS set to 2
    And the specialists are fakes that record what they receive

  @TP-SRS-003 @TP-SRS-062
  Scenario: A complete plan contains every part
    Given the specialists answer normally
    When I post a valid travel request to the Host
    Then the response status is 200
    And the plan has the fields "request_id", "trip_id", "flights", "stay", "activities", "errors", and "sources"
    And the plan has flights, stays, and activities
    And the plan's errors are empty

  @TP-SRS-060 @TP-SRS-141
  Scenario: The specialists are called at the same time
    Given each specialist takes 0.3 seconds to answer
    When I post a valid travel request to the Host
    Then the Host answers in less than 0.5 seconds
    And the Flight, Stay, and Activities agents each received the request once

  @TP-SRS-061 @TP-SRS-063 @TP-SRS-064 @TP-SRS-180
  Scenario Outline: A failed specialist does not stop the others
    Given the <agent> agent <failure>
    And the other specialists answer normally
    When I post a valid travel request to the Host
    Then the response status is 200
    And the plan's errors have one entry for "<part>" with message "Service is temporarily unavailable."
    And the plan has offers in the other two parts

    Examples:
      | agent      | part       | failure                                              |
      | Flight     | flights    | cannot be reached                                    |
      | Stay       | stay       | returns status 500                                   |
      | Activities | activities | returns invalid JSON                                 |
      | Flight     | flights    | returns JSON that does not match its response model  |
      | Stay       | stay       | takes 3 seconds to answer                            |

  @TP-SRS-064
  Scenario: A plan is still returned when every specialist fails
    Given every specialist returns status 500
    When I post a valid travel request to the Host
    Then the response status is 200
    And the plan's errors have one entry each for "flights", "stay", and "activities"
    And the plan has no offers

  @TP-SRS-065
  Scenario: Sources are merged without duplicates or malformed entries
    Given the specialists return these sources:
      | agent      | title       | url                                        | license      |
      | Flight     | Tokyo       | https://en.wikivoyage.org/wiki/Tokyo       | CC BY-SA 4.0 |
      | Stay       | Tokyo       | https://en.wikivoyage.org/wiki/Tokyo       | CC BY-SA 4.0 |
      | Activities | Tokyo/Ginza | https://en.wikivoyage.org/wiki/Tokyo/Ginza | CC BY-SA 4.0 |
      | Activities | Broken      |                                            | CC BY-SA 4.0 |
    When I post a valid travel request to the Host
    Then the plan's sources are:
      | title       | url                                        | license      |
      | Tokyo       | https://en.wikivoyage.org/wiki/Tokyo       | CC BY-SA 4.0 |
      | Tokyo/Ginza | https://en.wikivoyage.org/wiki/Tokyo/Ginza | CC BY-SA 4.0 |

  @TP-SRS-066
  Scenario: The Host never calls a language model
    Given the specialists answer normally
    And every language-model provider address is watched
    When I post a valid travel request to the Host
    Then the Host makes no request to any language-model provider

  @TP-SRS-004
  Scenario: An invalid request reaches no specialist
    When I post a travel request with travellers set to 0
    Then the response status is 422
    And no specialist receives a request
