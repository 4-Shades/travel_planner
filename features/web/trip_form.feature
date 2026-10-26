@web
Feature: Trip form
  As a traveler
  I want to describe my trip in a simple form
  So that I can ask for flight, stay, and activity suggestions

  Background:
    Given the planning service is available
    And I open the travel planner

  @TP-SRS-010 @TP-SRS-130
  Scenario: The form shows every trip field with a visible label
    Then I see a form with these labelled fields:
      | label          |
      | Origin         |
      | Destination    |
      | Start date     |
      | End date       |
      | Budget (USD)   |
      | Travellers     |

  @TP-SRS-011
  Scenario: Travellers defaults to one
    Then the "Travellers" field shows "1"

  @TP-SRS-011
  Scenario Outline: Travellers accepts whole numbers from 1 to 9
    When I enter "<value>" in the "Travellers" field
    Then the "Travellers" field is <validity>

    Examples:
      | value | validity |
      | 1     | valid    |
      | 9     | valid    |
      | 0     | invalid  |
      | 10    | invalid  |
      | 2.5   | invalid  |

  @TP-SRS-012
  Scenario Outline: Budget accepts amounts of at least 100 in steps of 50
    When I enter "<value>" in the "Budget (USD)" field
    Then the "Budget (USD)" field is <validity>

    Examples:
      | value | validity |
      | 100   | valid    |
      | 150   | valid    |
      | 5000  | valid    |
      | 99    | invalid  |
      | 125   | invalid  |
      | 50    | invalid  |

  @TP-SRS-013
  Scenario Outline: A trip without an origin or destination is not sent
    Given I have filled in the form with a valid trip
    When I clear the "<field>" field
    And I submit the form
    Then I see a warning that the <field> is required
    And no request is sent to the planning service

    Examples:
      | field       |
      | Origin      |
      | Destination |

  @TP-SRS-014
  Scenario Outline: A trip that does not end after it starts is not sent
    Given I have filled in the form with a valid trip
    When I set the start date to "2026-12-06"
    And I set the end date to "<end date>"
    And I submit the form
    Then I see a warning that the end date must be after the start date
    And no request is sent to the planning service

    Examples:
      | end date   |
      | 2026-12-06 |
      | 2026-12-05 |

  @TP-SRS-015
  Scenario: The submit button is disabled while a plan is requested
    Given the planning service takes 5 seconds to answer
    And I have filled in the form with a valid trip
    When I submit the form
    Then the submit button is disabled
    When the plan arrives
    Then the submit button is enabled

  @TP-SRS-130
  Scenario: A traveler can plan a trip with the keyboard alone
    When I fill in and submit the form using only the keyboard
    Then I see the trip results
