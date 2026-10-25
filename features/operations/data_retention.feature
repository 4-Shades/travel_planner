@api @host
Feature: Data retention
  As a traveler
  I want the planner to forget my trip once it has answered
  So that my plans are not stored anywhere

  @TP-SRS-150
  Scenario: Nothing from a request outlives it
    Given the Host and the specialists are running
    When I post a valid travel request with user_id "traveler-7"
    And the plan arrives
    Then no file in the application's data directories has changed
    And "traveler-7" appears nowhere except in log lines
