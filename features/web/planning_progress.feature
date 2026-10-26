@web
Feature: Planning progress
  As a traveler
  I want to see that my plan is being prepared and how it turned out
  So that I know whether to wait, read the results, or try again later

  Background:
    Given I open the travel planner
    And I have filled in the form with a valid trip

  @TP-SRS-020
  Scenario: Elapsed time is shown while the plan is requested
    Given the planning service takes 5 seconds to answer
    When I submit the form
    Then a progress indicator is shown at the top of the results area
    And it shows an elapsed time of 0 seconds
    When 3 seconds pass
    Then it shows an elapsed time of 3 seconds

  @TP-SRS-021
  Scenario: The indicator is complete when every part succeeded
    Given the planning service returns a plan with no errors
    When I submit the form
    Then the progress indicator shows the plan is complete

  @TP-SRS-021
  Scenario: The indicator is partial when a part failed
    Given the planning service returns a plan in which the flights part failed
    When I submit the form
    Then the progress indicator shows the plan is partial

  @TP-SRS-022 @TP-SRS-132
  Scenario Outline: The indicator fails when the planning service is unavailable
    Given the planning service <problem>
    When I submit the form
    Then the progress indicator shows the plan failed
    And I see the message "The planning service is unavailable. Please try again later."
    And the message mentions no provider name, stack trace, or key

    Examples:
      | problem                               |
      | cannot be reached                     |
      | returns status 500                    |
      | returns status 401                    |
      | does not answer within 180 seconds    |
